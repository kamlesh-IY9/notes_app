"""Persona sampling engine — generates unique personas for note generation."""

import random
import re
import logging
from pathlib import Path
from typing import Optional

import yaml
import gender_guesser.detector as gender_detector

log = logging.getLogger(__name__)
CONFIG_DIR = Path(__file__).parent.parent / "config"

# Probability of adding a surname to an Indian name (keeps it realistic)
_INDIA_SURNAME_PROB = 0.25


class PersonaSampler:
    """Samples unique personas from configured pools."""

    def __init__(self, language: str = "english"):
        self._language = language
        self._load_configs()
        self._gender_detector = gender_detector.Detector()
        self._used_names: set[str] = set()
        self._used_personas: list[dict] = []

    def switch_language(self, language: str):
        """Reload configs for a different language. Called at job start."""
        if language != self._language:
            self._language = language
            self._load_configs()
            log.info("PersonaSampler switched to language: %s", language)

    def _load_configs(self):
        if self._language == "hindi":
            personas_file = "india_personas.yaml"
            names_file = "india_names.yaml"
            rel_file = "india_relationships.yaml"
            topics_file = "india_topics.yaml"
        elif self._language == "arabic":
            personas_file = "arabic_personas.yaml"
            names_file = "arabic_names.yaml"
            rel_file = "arabic_relationships.yaml"
            topics_file = "arabic_topics.yaml"
        else:
            personas_file = "personas.yaml"
            names_file = "name_pools.yaml"
            rel_file = "relationships.yaml"
            topics_file = "topics.yaml"

        with open(CONFIG_DIR / personas_file) as f:
            self.persona_cfg = yaml.safe_load(f)
        with open(CONFIG_DIR / names_file) as f:
            self.name_pools = yaml.safe_load(f)
        with open(CONFIG_DIR / rel_file) as f:
            self.rel_cfg = yaml.safe_load(f)
        with open(CONFIG_DIR / topics_file) as f:
            self.topic_cfg = yaml.safe_load(f)

        # Parse states list (YAML inline format)
        raw_states = self.persona_cfg.get("states", [])
        self.states = []
        for item in raw_states:
            if isinstance(item, str):
                self.states.extend([s.strip() for s in item.split(" - ") if s.strip()])
        self.excluded_states = set(self.persona_cfg.get("excluded_states", []))
        self.states = [s for s in self.states if s not in self.excluded_states]

    def sample_persona(self) -> dict:
        """Sample a unique persona. Returns dict with all persona attributes."""
        max_attempts = 50
        for _ in range(max_attempts):
            persona = self._generate_persona()
            if persona["full_name"] not in self._used_names:
                self._used_names.add(persona["full_name"])
                self._used_personas.append(persona)
                return persona
        # Fallback: just generate and use it
        persona = self._generate_persona()
        self._used_names.add(persona["full_name"])
        self._used_personas.append(persona)
        return persona

    def _generate_persona(self) -> dict:
        # Age bracket
        age_brackets = self.persona_cfg["age_brackets"]
        weights = [b["weight"] for b in age_brackets]
        bracket = random.choices(age_brackets, weights=weights, k=1)[0]
        age = random.randint(bracket["range"][0], bracket["range"][1])

        # Gender
        genders = self.persona_cfg["genders"]
        g_weights = [g["weight"] for g in genders]
        gender = random.choices(genders, weights=g_weights, k=1)[0]["label"]

        # State
        state = random.choice(self.states)

        # Occupation
        occupation = random.choice(self.persona_cfg["occupations"])

        # Ethnicity
        ethnicities = self.persona_cfg["ethnicity_buckets"]
        ethnicity = random.choice(ethnicities)

        # Name from pool
        first_name = self._pick_name(gender, ethnicity)

        # Voice quirks (0-3)
        quirks_cfg = self.persona_cfg["voice_quirks"]
        num_quirks = random.choices([0, 1, 2, 3], weights=[20, 35, 30, 15], k=1)[0]
        quirk_weights = [q["weight"] for q in quirks_cfg]
        if num_quirks > 0:
            selected_quirks = random.choices(quirks_cfg, weights=quirk_weights,
                                              k=min(num_quirks, len(quirks_cfg)))
            # Deduplicate
            seen_ids = set()
            quirks = []
            for q in selected_quirks:
                if q["id"] not in seen_ids:
                    quirks.append(q["id"])
                    seen_ids.add(q["id"])
        else:
            quirks = []

        # For India/Arabic: optionally append a surname (~25% of the time)
        if self._language in ("hindi", "arabic") and random.random() < _INDIA_SURNAME_PROB:
            surname = self._pick_surname(ethnicity)
            full_name = f"{first_name} {surname}" if surname else first_name
        else:
            full_name = first_name

        return {
            "first_name": first_name,
            "full_name": full_name,
            "age": age,
            "age_bracket": bracket["label"],
            "gender": gender,
            "state": state,
            "occupation": occupation,
            "ethnicity": ethnicity,
            "voice_quirks": quirks,
        }

    def _pick_name(self, gender: str, ethnicity: str) -> str:
        """Pick a gender-appropriate name from the pool.

        Fallback chain stays inside the requested gender: try
        `(gender, ethnicity)` first, then any other ethnicity within the same
        gender, then the unisex nonbinary pool. Never silently crosses gender.
        """
        if gender == "nonbinary":
            pool_data = self.name_pools.get("nonbinary", {}).get("all", [])
        else:
            gender_key = gender  # "male" or "female"
            gender_pool = self.name_pools.get(gender_key, {})
            pool_data = gender_pool.get(ethnicity, [])
            # If requested ethnicity bucket is empty, fall back across
            # ethnicities WITHIN the same gender — never cross gender.
            if not pool_data:
                merged: list[str] = []
                for eth_pool in gender_pool.values():
                    if isinstance(eth_pool, list):
                        merged.extend(eth_pool)
                pool_data = merged
            # Last-resort fallback: unisex nonbinary pool (never the other gender)
            if not pool_data:
                pool_data = self.name_pools.get("nonbinary", {}).get("all", [])

        # Parse pool (YAML inline list with " - " separators)
        names = []
        for item in pool_data:
            if isinstance(item, str):
                names.extend([n.strip() for n in item.split(" - ") if n.strip()])

        if not names:
            names = ["Alex", "Sam", "Jordan", "Casey", "Morgan"]

        # Try to find an unused name
        available = [n for n in names if n not in self._used_names]
        if available:
            return random.choice(available)
        return random.choice(names)

    def _pick_surname(self, ethnicity: str) -> str:
        """Pick a regional surname for Indian personas (called ~25% of the time)."""
        surname_pools = self.name_pools.get("surnames", {})
        pool_data = surname_pools.get(ethnicity, [])
        if not pool_data:
            # Fallback to north_indian surnames
            pool_data = surname_pools.get("north_indian", [])
        names = []
        for item in pool_data:
            if isinstance(item, str):
                names.extend([n.strip() for n in item.split(" - ") if n.strip()])
        if not names:
            return ""
        return random.choice(names)

    def verify_name_gender(self, name: str, expected_gender: str) -> bool:
        """Verify name-gender consistency using gender-guesser."""
        if expected_gender == "nonbinary":
            return True  # Nonbinary names are intentionally ambiguous
        result = self._gender_detector.get_gender(name)
        if expected_gender == "female":
            return result in ("female", "mostly_female", "andy")
        elif expected_gender == "male":
            return result in ("male", "mostly_male", "andy")
        return True

    def sample_relationship(self) -> dict:
        """Sample a relationship type."""
        rels = self.rel_cfg["relationships"]
        weights = [r["weight"] for r in rels]
        return random.choices(rels, weights=weights, k=1)[0]

    def sample_topic(self) -> dict:
        """Sample a topic."""
        topics = self.topic_cfg["topics"]
        weights = [t["weight"] for t in topics]
        return random.choices(topics, weights=weights, k=1)[0]

    def sample_mood(self) -> str:
        """Sample a mood/tone for the note."""
        moods = [
            "neutral", "happy", "frustrated", "worried", "excited",
            "nostalgic", "annoyed", "grateful", "stressed", "hopeful",
            "tired", "amused", "sad", "relieved", "confused",
        ]
        weights = [15, 12, 10, 10, 8, 8, 8, 7, 6, 5, 4, 3, 3, 3, 2]
        return random.choices(moods, weights=weights, k=1)[0]

    def sample_related_name(self, persona: dict, relationship: dict) -> tuple[str, str]:
        """Pick a name + gender for the person mentioned in the note.

        Returns (name, gender). Gender is one of "male" / "female" / "nonbinary"
        and must be used by the caller to pick a gender-matching relationship label.
        Picked name is added to _used_names to prevent intra-batch repeats.
        """
        rel_id = relationship["id"]

        # Honor explicit relationship-level pronoun / same_gender flags first
        if relationship.get("pronouns") == ["they", "them", "their"]:
            related_gender = "nonbinary"
        elif relationship.get("same_gender") is True:
            related_gender = persona["gender"] if persona["gender"] in ("male", "female") else random.choice(["male", "female"])
        elif relationship.get("same_gender") == "any":
            related_gender = random.choice(["male", "female"])
        # Determine gender of related person based on relationship
        elif rel_id == "partner":
            # Usually opposite gender, but not always
            if persona["gender"] == "male":
                related_gender = random.choices(["female", "male"], weights=[85, 15], k=1)[0]
            elif persona["gender"] == "female":
                related_gender = random.choices(["male", "female"], weights=[85, 15], k=1)[0]
            else:
                related_gender = random.choice(["male", "female"])
        elif rel_id == "parent":
            related_gender = random.choice(["male", "female"])
        elif rel_id == "sibling":
            related_gender = random.choice(["male", "female"])
        elif rel_id == "child":
            related_gender = random.choice(["male", "female"])
        else:
            related_gender = random.choice(["male", "female"])

        name = self._pick_name(related_gender, persona["ethnicity"])
        self._used_names.add(name)
        return name, related_gender

    def reset(self):
        """Reset used names for a new batch."""
        self._used_names.clear()
        self._used_personas.clear()
        log.debug("PersonaSampler reset (language=%s)", self._language)
