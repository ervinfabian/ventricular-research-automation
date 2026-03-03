import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

def merge_separate_spreadsheets(json_key_path, original_data_file, segment_data_file, output_file):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_key_path, scope)
    client = gspread.authorize(creds)

    print("Forrásfájlok megnyitása...")
    file_orig = client.open(original_data_file)
    file_seg = client.open(segment_data_file)
    
    # Adatok beolvasása nyers szövegként (ezzel kikerüljük a get_all_records hibáit)
    def get_clean_df(ws):
        data = ws.get_all_values()
        if not data:
            return pd.DataFrame()
        # Első sor a fejléc, a többi az adat
        df = pd.DataFrame(data[1:], columns=data[0])
        return df

    df_original = get_clean_df(file_orig.get_worksheet(0))
    df_segment = get_clean_df(file_seg.get_worksheet(0))

    print("Egyesítés 'case_id' alapján...")
    # Kényszerítjük, hogy a case_id szöveg legyen a biztos kapcsolódáshoz
    df_original['case_id'] = df_original['case_id'].astype(str).str.strip()
    df_segment['case_id'] = df_segment['case_id'].astype(str).str.strip()

    # Összefűzés
    merged_df = pd.merge(df_segment, df_original, on='case_id', how='left', suffixes=('', '_drop'))
    merged_df = merged_df.drop([c for c in merged_df.columns if '_drop' in c], axis=1)

    # SZÁMOK JAVÍTÁSA: Itt dől el a 0.33 sorsa
    numeric_cols = ['evans_index', 'frontal_horn', 'full_width', 
                   'brain', 'lateral_ventricle', 
                   'third_ventricle', 'fourth_ventricle', 'subarachnoid']

    for col in numeric_cols:
        if col in merged_df.columns:
            # 1. Minden értéket szöveggé alakítunk
            # 2. A vesszőt pontra cseréljük (hogy a Python értse)
            # 3. Számmá alakítjuk
            merged_df[col] = (
                merged_df[col]
                .astype(str)
                .str.replace(',', '.')
                .replace('', '0') # Az üreseket nullázzuk a biztonság kedvéért
            )
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce')

    print(f"Mentés a '{output_file}' fájlba...")
    file_out = client.open(output_file)
    
    # Megpróbáljuk megnyitni a 'data' fület, ha nincs, létrehozzuk
    try:
        output_ws = file_out.worksheet("data")
        output_ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        output_ws = file_out.add_worksheet(title="data", rows="1000", cols="30")

    # Feltöltés a pontos számokkal
    set_with_dataframe(output_ws, merged_df, include_index=False)
    
    print(f"Siker! A tizedesjegyek (pl. 0.33) megmaradtak. Összesen {len(merged_df)} sor mentve.")

# INDÍTÁS
merge_separate_spreadsheets(
    "/Users/ervin/Documents/kutatas/brain-ventricles-study-7b0925fa71d3.json", 
    'Original-data', 
    'Segment-data4',     
    'Original-data'      
)