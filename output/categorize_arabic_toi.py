import os
from pathlib import Path

# Paths
TXT_DIR = Path("/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/output/sample arabic b1 TOI/txt")

# Arabic Category mapping keywords
CAT_MAP = {
    "finance stocks portfolio": ["مالي", "استثمار", "أسهم", "أرامكو", "تداول", "اقتصاد", "ضريبة", "بنك", "تمويل", "صكوك", "حلال", "اكتتاب", "أدنوك", "سعر", "الذهب", "الرهن", "العقاري", "قرض", "ائتمان", "راتب"],
    "technology": ["تكنولوجيا", "نموذج", "ذكاء", "اصطناعي", "برمجة", "معالجة", "لغوية", "عصبية", "انتباه", "آليات", "حوسبة", "رقمي", "بيانات", "خوارزمية", "التضمين", "منصة", "شاهد", "تطبيق", "تطوير", "تقنية"],
    "government politics": ["سياسة", "نقدية", "لوائح", "قانون", "مجلس", "تعاون", "إمارات", "دبي", "خليج", "حكومة", "دول", "مركز", "المالي", "الرواتب", "خصخصة", "وزارة", "تقرير", "سنوي", "هيئة"],
    "academic professional": ["دراسة", "تحليل", "ملاحظات", "أبحاث", "تجربة", "فيزياء", "كيمياء", "هندسة", "فلك", "تقويم", "فقهية", "تاريخ", "تفسير", "تصنيف", "الحديث", "بيم", "بروتين", "تحلية", "طاقة"],
    "weather": ["حرارة", "طقس", "مناخ", "رياح", "مطر", "صيف", "شتاء", "رطوبة", "ضباب", "جفاف", "غبار"],
    "food": ["طبخ", "أرز", "مندي", "بخار", "حليب", "إبل", "سمن", "خبز", "عربي", "قمح", "طعام"],
    "health fitness": ["علاج", "طبيعي", "تمارين", "رياضة", "صحة", "جراحة", "طب", "بدني", "لياقة", "الجسم", "القدرة", "الهوائية", "كروسفيت", "صيام", "التهام", "عضلات"],
    "sports": ["كرة", "قدم", "دوري", "اسكواش", "تدريب", "هدف", "لاعب", "بطولة", "صقارة", "كأس", "العالم", "القوة", "ماراثون", "صيد"],
    "automotive": ["سيارات", "محرك", "إطارات", "شحن", "كهرباء", "حافلة", "مرور", "قيادة", "النقل", "مترو", "طيران", "ملاحي", "سفن", "بحرية"],
}

def get_category(title, content):
    text = (title + " " + content).lower()
    # Check for strongest matches first or specific order
    for cat, keywords in CAT_MAP.items():
        if any(kw in text for kw in keywords):
            return cat
    return "academic professional" # Default

def process():
    # Use pattern matching to get 001 to 100 in order
    results = []
    for i in range(1, 101):
        filename = f"DS104_TOI_Notes_AR_AE_B1_{i:03d}.txt"
        filepath = TXT_DIR / filename
        if not filepath.exists():
            # Try SA naming if AE doesn't exist
            filename = f"DS104_TOI_Files_AR_SA_B1_{i:03d}.pdf"
            # Actually the text files are in the txt dir, check their names
            # Based on list_dir, they are DS104_TOI_Notes_AR_AE_B1_XXX.txt
            results.append("academic professional") # Placeholder
            continue
            
        try:
            lines = filepath.read_text(encoding='utf-8').split('\n')
            title = lines[0] if lines else ""
            content = " ".join(lines[1:])
            category = get_category(title, content)
            results.append(category)
        except:
            results.append("academic professional")
        
    for cat in results:
        print(cat)

if __name__ == "__main__":
    process()
