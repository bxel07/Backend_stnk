import re

regex_vin = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')  # Validasi VIN global
regex_alnum = re.compile(r'^[A-Z0-9]+$')

kode_negara_indonesia = [f"M{chr(c)}" for c in range(ord("F"), ord("K")+1)]  # MF - MK
kode_pabrikan_indonesia = {
    'Y': 'Suzuki',
    'F': 'Toyota',
    'R': 'Honda',
    'K': 'Daihatsu',
}

def cek_vin_indonesia(vin):
    """Validasi apakah VIN dirakit di Indonesia dan milik pabrikan yang dikenal"""
    vin = vin.strip().upper()
    if len(vin) != 17 or not regex_vin.match(vin):
        return None

    prefix_2 = vin[:2]
    prod_code = vin[2]

    lokasi = "Indonesia" if prefix_2 in kode_negara_indonesia else "Bukan Indonesia"
    pabrikan = kode_pabrikan_indonesia.get(prod_code, "Tidak diketahui")

    return {
        "lokasi_perakitan": lokasi,
        "pabrikan": pabrikan,
        "kode_negara": prefix_2,
        "kode_pabrikan": prod_code
    }

def extract_nomor_rangka_fast(ocr_output):
    """
    Ekstraksi dan validasi ketat nomor rangka (VIN) dari hasil OCR STNK.
    """
    all_texts = [
        text.strip()
        for res in ocr_output
        for text in res.get('rec_texts', [])
        if text.strip()
    ]
    upper_texts = [t.upper() for t in all_texts]

    # --- Method 1: Berdasarkan teks label ---
    for i, text in enumerate(upper_texts):
        if "NOMOR RANGKA/NIK/VIN" in text or "NOMOR RANGKA" in text:
            for candidate in upper_texts[i+1:i+4]:
                vin = candidate.strip().upper()
                if len(vin) == 17 and regex_vin.match(vin):
                    info = cek_vin_indonesia(vin)
                    if info:
                        return vin, info, all_texts

    # --- Method 2: Pencarian brute-force dari semua teks OCR ---
    for text in upper_texts:
        vin = text.strip().upper()
        if len(vin) == 17 and regex_vin.match(vin):
            info = cek_vin_indonesia(vin)
            if info:
                return vin, info, all_texts

    # --- Method 3: Pendekatan posisi horizontal label -> value ---
    if isinstance(ocr_output, list):
        for entry in ocr_output:
            if 'dt_polys' in entry and 'rec_texts' in entry:
                candidate, _ = extract_from_position(entry)
                vin = candidate.strip().upper() if candidate else ''
                if len(vin) == 17 and regex_vin.match(vin):
                    info = cek_vin_indonesia(vin)
                    if info:
                        return vin, info, all_texts

    # --- Tidak ditemukan VIN valid ---
    # Initialize variables to avoid UnboundLocalError
    vin = None
    info = None
    print(f"Debug: vin={vin}, info={info}, found_texts_count={len(all_texts)}")
    return None, None, all_texts

def extract_from_position(ocr_result_dict, label_keywords=None, x_offset_min=5, y_tolerance=15):
    """Ekstrak berdasarkan posisi relatif horizontal dari label ke nilai"""
    if label_keywords is None:
        label_keywords = ['NOMOR RANGKA', 'NO RANGKA', 'RANGKA', 'CHASSIS', 'VIN']

    polys = ocr_result_dict.get('dt_polys', [])
    texts = ocr_result_dict.get('rec_texts', [])

    if not polys or not texts or len(polys) != len(texts):
        return None, None

    for i, label_text in enumerate(texts):
        label_text_upper = label_text.strip().upper()
        for keyword in label_keywords:
            if keyword in label_text_upper:
                label_box = polys[i]
                label_y_center = (label_box[0][1] + label_box[2][1]) / 2
                label_x_end = max(pt[0] for pt in label_box)

                for j, candidate_box in enumerate(polys):
                    if j == i:
                        continue
                    candidate_text = texts[j].strip()
                    if not candidate_text:
                        continue

                    candidate_x_start = min(pt[0] for pt in candidate_box)
                    candidate_y_center = (candidate_box[0][1] + candidate_box[2][1]) / 2

                    if (candidate_x_start > label_x_end + x_offset_min and
                        abs(candidate_y_center - label_y_center) <= y_tolerance):

                        if 15 <= len(candidate_text) <= 20 and regex_alnum.match(candidate_text.upper()):
                            return candidate_text.strip(), label_text_upper
    return None, None