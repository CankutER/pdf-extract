import re

# Two pointers to scan above & below image line and skip empty lines
def scan_image_labels(lines,i,window_range=20):
 up_offset=1
 up_slider = 1
 down_offset = 1
 down_slider = 1
 up_candidate =""
 down_candidate= ""
 up_threshold=False
 down_threshold=False
 while up_slider < window_range+1 or down_slider < window_range+1:
    if i - up_offset>=0:
        line_above = lines[i - up_offset].strip()
    else:
       line_above=""
       up_slider+=1
       up_threshold=True

    if i + down_offset<len(lines):
       line_below = lines[i + down_offset].strip()
    else:
       line_below=""
       down_slider+=1
       down_threshold=True
              
    up_offset+=1
    down_offset+=1
    if (line_above and not re.match(r'\n',line_above) and not up_candidate) and not up_threshold:
        if re.search(r'(Figure|Table|Figür|Tablo|Şekil|Grafik|Diagram|Chart|Diyagram)\s?\d+', line_above, re.IGNORECASE):
            up_candidate=line_above
        up_slider+=1
    if (line_below and not re.match(r'\n',line_below) and not down_candidate) and not down_threshold:
        if re.search(r'(Figure|Table|Figür|Tablo|Şekil|Grafik|Diagram|Chart|Diyagram)\s?\d+', line_below, re.IGNORECASE):
            down_candidate=line_below
        down_slider+=1

 return down_candidate or up_candidate


#Same logic with image label scan, except table start and ends are different lines
def scan_table_labels(lines,table_start,table_end,window_range=20):
 up_offset=1
 up_slider = 1
 down_offset = 1
 down_slider = 1
 up_candidate =""
 down_candidate= ""
 up_threshold=False
 down_threshold=False
 while up_slider < window_range+1 or down_slider < window_range+1:
    if table_start - up_offset>=0:
        line_above = lines[table_start - up_offset].strip()
    else:
       line_above=""
       up_slider+=1
       up_threshold=True

    if table_end + down_offset<len(lines):
       line_below = lines[table_end + down_offset].strip()
    else:
       line_below=""
       down_slider+=1
       down_threshold=True   

    up_offset+=1
    down_offset+=1
    if (line_above and not re.match(r'\n',line_above) and not up_candidate) and not up_threshold:
        if re.search(r'(Table|Tablo)\s?\d+', line_above, re.IGNORECASE):
            up_candidate=line_above
        up_slider+=1
    if (line_below and not re.match(r'\n',line_below) and not down_candidate) and not down_threshold:
        if re.search(r'(Table|Tablo)\s?\d+', line_below, re.IGNORECASE):
            down_candidate=line_below
        down_slider+=1

 return up_candidate or down_candidate


#Check if words are capitalized or full uppercase to detect a possible header
def is_capitalized_or_uppercase(text):
    stopwords = {
        # English stopwords
        "the", "and", "is", "in", "on", "for", "to", "of", "a", "an", "by", "with", "at", "from",
        "that", "this", "these", "those", "as", "it", "its", "be", "are", "was", "were", "or", "but",

        # Turkish stopwords
        "ve", "ile", "bir", "bu", "şu", "o", "da", "de", "için", "ama", "fakat", "ya", "veya", "gibi",
        "en", "mi", "mı", "mu", "mü", "ki", "ne",
    }

    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", text)
    if not words:
        return False

    # filter out stopwords before checking capitalization
    filtered_words = [w for w in words if w.lower() not in stopwords]
    if not filtered_words:
        return False

    result = all(w[0].isupper() or w.isupper() for w in filtered_words) and len(filtered_words) <= 10
    return result
