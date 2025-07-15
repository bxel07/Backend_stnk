import re
import os
import time
import glob
from paddlex import create_pipeline # Pastikan paddlex terinstal

# ==============================================================================
# BAGIAN 1: KONSTANTA GLOBAL & FUNGSI VALIDASI
# (Tidak ada perubahan di bagian ini)
# ==============================================================================
KNOWN_WMIS = [
    'JA3', 'JA4', 'JC1', 'JDA', 'JF1', 'JF2', 'JF3', 'JF4', 'JHM', 'JHF', 'JHL', 'JHG', 'JHH', 
    'JMA', 'JMB', 'JMC', 'JMD', 'JME', 'JMF', 'JMG', 'JN1', 'JN3', 'JN4', 'JN5', 'JN6', 'JN8', 
    'JS2', 'JSA', 'JT1', 'JTD', 'JTE', 'JTH', 'JTK', 'JTL', 'KNA', 'KNB', 'KNC', 'KNE', 'KMH', 
    'KMF', 'KMG', 'KPA', 'LBE', 'LBV', 'LC0', 'LDC', 'LE4', 'LFM', 'LFP', 'LGL', 'LGX', 'LHG', 
    'LJD', 'LSG', 'LSJ', 'LSV', 'LUX', 'LVG', 'LVH', 'LVS', 'LVV', 'LZW', 'MHF', 'MHR', 'MFK', 
    'MFF', 'MFY', 'MJK', 'MGY', 'MLH', 'ML0', 'MMB', 'MMC', 'MMT', 'MMS', 'MNB', 'MPA', 'MPB', 
    'MRH', 'MR0', 'MA1', 'MA3', 'MA6', 'MA7', 'MAL', 'MAT', 'MC2', 'MEE', 'MNT', 'TRU', 'WAU', 
    'WUA', 'WBA', 'WBS', 'WBX', 'WDB', 'WDD', 'WMA', 'WMW', 'W0L', 'WVW', 'WV1', 'WV2', 'WP0', 
    'WP1', 'SAJ', 'SAL', 'SAR', 'SCC', 'SCF', 'SDB', 'SFD', 'SHS', 'SJN', 'TW2', 'ZAM', 'ZAR', 
    'ZCF', 'ZFA', 'ZFF', 'ZHW', 'ZLA', 'VF1', 'VF2', 'VF3', 'VF7', 'VNK', 'YSM', 'YS2', 'YS3', 
    'YV1', 'YV2', 'YV3', 'YV4', 'TMB', 'TM9', 'U5Y', 'UU1', 'VSX', '1B3', '1C3', '1C6', '1F9', 
    '1FA', '1FB', '1FC', '1FD', '1FM', '1FT', '1G1', '1G2', '1G3', '1G4', '1G6', '1G8', '1GC', 
    '1GN', '1HG', '1M1', '1M2', '1M3', '1M4', '1N2', '1N4', '1N6', '1VW', '2FT', '3FE', '3F7', 
    '4F2', '4S3', '4T1', '4T3', '4US', '5F4', '5FN', '5FR', '5GA', '5J6', '5J8', '5L9', '5LM', 
    '5NM', '5NP', '5T2', '5T4', '5TD', '5TE', '5YJ', '5XX', '2C3', '2FA', '2FD', '2FM', '2FT', 
    '2G1', '2G2', '2G3', '2G4', '2HG', '2M1', '2M2', '2T1', '2T2', '3C3', '3C4', '3C6', '3FA', 
    '3FE', '3FR', '3G1', '3G2', '3G3', '3G4', '3G7', '3GC', '3GN', '3HG', '3HM', '3N1', '3N3', 
    '3N4', '3VW'
]
NEGATIVE_KEYWORDS = [
    'KENDARAAN', 'RANGKA', 'NOMOR', 'POLISI', 'PEMILIK', 'MERK', 'TIPE', 
    'MODEL', 'MESIN', 'TAHUN', 'WARNA', 'SNO', 'JAYG', 'INDONESIAN',
    'KEPOLISIAN', 'SERTIFIKAT', 'REGISTRASI', 'VALIDATION'
]
ANCHOR_KEYWORDS = ['RANGKA', 'NIKNIN'] 
KODE_TAHUN = {'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014, 'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029, 'Y': 2030, '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005, '6': 2006, '7': 2007, '8': 2008, '9': 2009}

def decode_wmi_global(wmi: str):
    country = "Negara tidak terdaftar"
    manufacturer = "Pabrikan tidak terdaftar"
    first_char = wmi[0]
    second_char = wmi[1]
    if 'J' == first_char: country = 'Jepang'
    elif 'K' == first_char: country = 'Korea Selatan'
    elif 'L' == first_char: country = 'Cina'
    elif 'M' == first_char:
        if 'A' <= second_char <= 'E': country = 'India'
        elif 'F' <= second_char <= 'K':
            country = 'Indonesia'
            indo_manufacturers = {'Y': 'Suzuki', 'F': 'Toyota', 'R': 'Honda', 'K': 'Daihatsu'}
            manufacturer = indo_manufacturers.get(wmi[2], f"Pabrikan Indonesia tidak terdaftar ({wmi[2]})")
        elif 'L' <= second_char <= 'R': country = 'Thailand'
    elif 'P' == first_char: country = 'Filipina / Malaysia'
    elif 'R' == first_char: country = 'Vietnam / Taiwan'
    elif first_char in ['1', '4', '5']: country = 'Amerika Serikat'
    elif first_char == '2': country = 'Kanada'
    elif first_char == '3': country = 'Meksiko'
    elif 'S' == first_char: country = 'Eropa (Utama: Inggris, Jerman, Polandia)'
    elif 'T' == first_char: country = 'Eropa (Utama: Swiss, Rep. Ceko, Hungaria)'
    elif 'U' == first_char: country = 'Eropa (Utama: Denmark, Irlandia, Romania, Slovakia)'
    elif 'V' == first_char: country = 'Eropa (Utama: Prancis, Spanyol, Austria)'
    elif 'W' == first_char: country = 'Jerman'
    elif 'X' == first_char: country = 'Eropa (Utama: Rusia & Negara CIS)'
    elif 'Y' == first_char: country = 'Eropa (Utama: Belgia, Finlandia, Swedia)'
    elif 'Z' == first_char: country = 'Italia'
    
    if manufacturer == "Pabrikan tidak terdaftar" and country != "Negara tidak terdaftar":
        manufacturer = f"Pabrikan terdaftar di {country} (Kode WMI: {wmi})"
    return {"country": country, "manufacturer": manufacturer}

def validate_and_parse_vin_global(vin: str):
    vin_upper = vin.strip().upper()
    safe_normalized_vin = vin_upper.replace('O', '0').replace('I', '1').replace('Z','2')
    if len(safe_normalized_vin) != 17 or not safe_normalized_vin.isalnum():
        return {"is_valid": False, "vin": vin_upper, "error_message": "VIN harus 17 karakter alfanumerik."}
    wmi, vds, vis = safe_normalized_vin[0:3], safe_normalized_vin[3:9], safe_normalized_vin[9:17]
    vds_final = vds.replace('S', '5').replace('B', '8')
    vis_final = vis.replace('S', '5').replace('B', '8')
    final_vin = wmi + vds_final + vis_final
    regex_iso = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    if not regex_iso.match(final_vin):
        return {"is_valid": False, "vin": final_vin, "error_message": f"Format VIN tidak valid."}
    year_code = final_vin[9]
    wmi_info = decode_wmi_global(wmi)
    asal_kendaraan = wmi_info["country"]
    pabrikan = wmi_info["manufacturer"]
    if asal_kendaraan == "Negara tidak terdaftar":
        return {"is_valid": False, "vin": final_vin, "error_message": f"Kode Negara/WMI '{wmi}' tidak dikenali."}
    tahun_kendaraan = KODE_TAHUN.get(year_code)
    if not tahun_kendaraan:
        return {"is_valid": False, "vin": final_vin, "error_message": f"Kode tahun perakitan '{year_code}' tidak valid."}
    return {"is_valid": True, "vin": final_vin, "wmi": wmi, "vds": vds_final, "vis": vis_final, "country_of_origin": asal_kendaraan, "manufacturer": pabrikan, "vehicle_year": tahun_kendaraan, "error_message": None}

# ==============================================================================
# BAGIAN 2: FUNGSI PENILAIAN & METODE EKSTRAKSI
# (Tidak ada perubahan di bagian ini)
# ==============================================================================
def calculate_vin_likeness_score(text: str):
    score = 0
    upper_text = text.upper()
    cleaned_text = re.sub(r'[^A-Z0-9]', '', upper_text)
    if not cleaned_text: return -100
    if any(wmi in upper_text for wmi in KNOWN_WMIS): score += 50
    if any(keyword in upper_text for keyword in ANCHOR_KEYWORDS): score += 40
    density = len(cleaned_text) / len(text) if len(text) > 0 else 0
    score += int(density * 20)
    # Check for longest alphanumeric block
    longest_block_len = 0
    if cleaned_text:
        # Split by non-alphanumeric characters in the original upper_text to find blocks
        blocks = re.split(r'[^A-Z0-9]+', upper_text)
        longest_block_len = max(len(block) for block in blocks) if blocks else 0
        
    if longest_block_len >= 17: score += 25
    elif longest_block_len >= 10: score += 10
    if any(symbol in text for symbol in ['.', '-', '/']): score -= 20
    word_count = len(text.split())
    if word_count > 2: score -= (word_count * 5)
    num_digits = sum(c.isdigit() for c in cleaned_text)
    digit_ratio = num_digits / len(cleaned_text) if cleaned_text else 0
    if digit_ratio > 0.9 and len(cleaned_text) > 15: score -= 40
    if any(keyword in upper_text for keyword in NEGATIVE_KEYWORDS): score -= 5
    return score

def metode_1_berbasis_anchor(texts):
    candidate_pattern = re.compile(r'[A-Z0-9]{17}')
    for i, text in enumerate(texts):
        if 'RANGKA' in text.upper():
            search_window_list = texts[i : i+2] 
            for line_in_window in search_window_list:
                cleaned_line = re.sub(r'[^A-Z0-9]', '', line_in_window.upper())
                for candidate in candidate_pattern.findall(cleaned_line):
                    if any(keyword in candidate for keyword in NEGATIVE_KEYWORDS): continue
                    validation_result = validate_and_parse_vin_global(candidate)
                    if validation_result["is_valid"]:
                        validation_result["found_by_method"] = "Metode 1 (Anchor 'RANGKA')"
                        return validation_result
    return {"is_valid": False}

def metode_2_berbasis_wmi(texts):
    for line in texts:
        cleaned_line = re.sub(r'[^A-Z0-9]', '', line.upper())
        for wmi in KNOWN_WMIS:
            if wmi in cleaned_line:
                start_index = cleaned_line.find(wmi)
                candidate = cleaned_line[start_index : start_index + 17]
                if len(candidate) == 17:
                    if any(keyword in candidate for keyword in NEGATIVE_KEYWORDS): continue
                    validation_result = validate_and_parse_vin_global(candidate)
                    if validation_result["is_valid"]:
                        validation_result["found_by_method"] = "Metode 2 (WMI Terpandu)"
                        return validation_result
    return {"is_valid": False}

def metode_3_brute_force_regex(texts):
    strict_pattern = re.compile(r'[A-HJ-NPR-Z0-9]{17}')
    for line in texts:
        cleaned_line = re.sub(r'[^A-Z0-9]', '', line.upper())
        for candidate in strict_pattern.findall(cleaned_line):
            if any(keyword in candidate for keyword in NEGATIVE_KEYWORDS): continue
            validation_result = validate_and_parse_vin_global(candidate)
            if validation_result["is_valid"]:
                validation_result["found_by_method"] = "Metode 3 (Brute-force Regex)"
                return validation_result
    return {"is_valid": False}

def metode_4_fuzzy_wmi_recovery(texts):
    for line in texts:
        for wmi in KNOWN_WMIS:
            pos = line.upper().find(wmi)
            if pos != -1:
                tail_string = line[pos:]
                cleaned_tail = re.sub(r'[^A-Z0-9]', '', tail_string.upper())
                if len(cleaned_tail) >= 17:
                    candidate = cleaned_tail[:17]
                    if any(keyword in candidate for keyword in NEGATIVE_KEYWORDS): continue
                    validation_result = validate_and_parse_vin_global(candidate)
                    if validation_result["is_valid"]:
                        validation_result["found_by_method"] = "Metode 4 (Fuzzy WMI Recovery)"
                        return validation_result
    return {"is_valid": False}

# ==============================================================================
# BAGIAN 3: FUNGSI ORKESTRASI (PAKAR)
# (Tidak ada perubahan di bagian ini)
# ==============================================================================
def extract_vin_pakar(texts):
    # Dihapus print() untuk production API agar log lebih bersih
    hasil = metode_1_berbasis_anchor(texts)
    if hasil.get("is_valid"): return hasil
    hasil = metode_2_berbasis_wmi(texts)
    if hasil.get("is_valid"): return hasil
    hasil = metode_3_brute_force_regex(texts)
    if hasil.get("is_valid"): return hasil
    hasil = metode_4_fuzzy_wmi_recovery(texts)
    if hasil.get("is_valid"): return hasil
    return {"is_valid": False, "error_message": "VIN yang valid tidak dapat ditemukan setelah mencoba semua metode."}

# ==============================================================================
# BAGIAN 4: PROSESOR UNTUK SATU GAMBAR
# (Tidak ada perubahan di bagian ini)
# ==============================================================================
def process_single_image(pipeline, image_path: str, candidate_count: int):
    """
    Melakukan OCR dan ekstraksi VIN pada satu file gambar.
    Mengembalikan dictionary hasil jika valid, atau dictionary error jika gagal.
    """
    if not os.path.exists(image_path):
        return {"is_valid": False, "error_message": f"File tidak ditemukan: {os.path.basename(image_path)}"}
    
    try:
        hasil_ocr_list = list(pipeline.predict(input=image_path, use_doc_unwarping=False, use_textline_orientation=True, use_doc_orientation_classify=False))
        
        if not hasil_ocr_list or not hasil_ocr_list[0].get('rec_texts'):
            return {"is_valid": False, "error_message": "OCR tidak mendeteksi teks apa pun."}

        rec_texts = hasil_ocr_list[0]['rec_texts']
        scored_texts = sorted([(calculate_vin_likeness_score(text), text) for text in rec_texts], key=lambda x: x[0], reverse=True)
        final_candidates = [text for score, text in scored_texts[:candidate_count]]
        
        return (final_candidates)

    except Exception as e:
        return {"is_valid": False, "error_message": f"Terjadi exception saat pemrosesan OCR: {e}"}


# ==============================================================================
# PERUBAHAN UTAMA: BAGIAN 5 - FUNGSI UTAMA YANG AKAN DIPANGGIL API
# Fungsi ini menggantikan `main()` lama Anda.
# ==============================================================================

def run_batch_processing(batch_directory: str, pipeline_path: create_pipeline, candidate_count: int = 10, db: Session = None):
    import time, os, glob
    from app.models import master_excel

    start_total_time = time.time()

    try:
        pipeline = pipeline_path
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saat load pipeline: {e}"
        }

    image_extensions = ('*.jpg', '*.jpeg', '*.png')
    image_paths = []
    for ext in image_extensions:
        image_paths.extend(glob.glob(os.path.join(batch_directory, ext)))

    if not image_paths:
        return {
            "status": "error",
            "message": f"Tidak ada file gambar valid di '{batch_directory}'"
        }

    # ✅ Ambil data dari database
    norangka_map = {
        row.norangka: {
            "samsat": row.samsat,
            "kode_samsat": row.kode_samsat,
            "merk": row.merk
        } for row in db.query(master_excel).all()
    }

    all_results = []
    success_count = 0
    fail_count = 0

    for image_path in image_paths:
        filename = os.path.basename(image_path)
        vin_result = process_single_image(pipeline, image_path, candidate_count)
        full_path = os.path.join(batch_directory, filename)

        nomor_rangka = vin_result.get("vin")
        matched_info = norangka_map.get(nomor_rangka, {"samsat": "-", "kode_samsat": "-", "merk": "-"})

        if vin_result.get("is_valid"):
            success_count += 1
            formatted_result = {
                "filename": filename,
                "path": full_path,
                "status": "success",
                "nomor_rangka": nomor_rangka,
                "details": {
                    "found_by_method": vin_result.get("found_by_method"),
                    "asal_kendaraan": vin_result.get("country_of_origin"),
                    "pabrikan": vin_result.get("manufacturer"),
                    "tahun_kendaraan": vin_result.get("vehicle_year"),
                    "jumlah": vin_result.get("jumlah") or 0,
                    # ✅ Tambahan:
                    "samsat": matched_info["samsat"],
                    "kode_samsat": matched_info["kode_samsat"],
                    "merk": matched_info["merk"],
                },
                "error_message": None
            }
        else:
            fail_count += 1
            formatted_result = {
                "filename": filename,
                "path": full_path,
                "status": "failed",
                "nomor_rangka": None,
                "details": None,
                "error_message": vin_result.get("error_message", "Unknown error")
            }

        all_results.append(formatted_result)

    total_duration = time.time() - start_total_time

    return {
        "status": "completed",
        "message": f"Proses batch selesai. {success_count} berhasil, {fail_count} gagal.",
        "summary": {
            "total_images": len(image_paths),
            "success_count": success_count,
            "fail_count": fail_count,
            "total_duration_seconds": round(total_duration, 2),
            "average_duration_per_image_seconds": round(total_duration / len(image_paths), 2) if image_paths else 0
        },
        "results": all_results
    }
