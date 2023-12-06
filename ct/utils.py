import re
import pandas as pd

def read_consurf_grade_file(file_path: str) -> pd.DataFrame:
    """
    Read consurf_grade file from consurf web server and return a pandas dataframe
    :param file_path: path to the consurf_grade file
    :return: pandas dataframe
    """
    column_names = [
        'POS', 'SEQ', 'SCORE', 'COLOR', 'CONFIDENCE_INTERVAL',
        'CONFIDENCE_INTERVAL_COLORS', 'MSA_DATA', 'RESIDUE_VARIETY', 'B/E', 'FUNCTION'
    ]
    patterns = {
        'POS': r'\d+',
        'SEQ': r'[A-Z]',
        'SCORE': r'-?\d+\.\d{1,3}',
        'COLOR': r'\w\**',
        'CONFIDENCE_INTERVAL': r'-?\d+\.\d{1,3},\s+-?\d+\.\d{1,3}',
        'CONFIDENCE_INTERVAL_COLORS': r'\d,\d',
        'B/E': r'[be]',
        'FUNCTION': r'[fs]',
        'MSA_DATA': r'\d+/\d+',
        'RESIDUE_VARIETY': r'[A-Z](, [A-Z])*'
    }
    compiled_patterns = {col: re.compile(pat) for col, pat in patterns.items()}
    started = False
    with open(file_path, "rt") as f:
        data = []
        for line in f:
            row = {}
            if line.startswith("*") or line.startswith("or"):
                continue
            if not started:
                if all([i.replace("_", " ") in line for i in column_names]):
                    started = True
            else:
                if line.strip() == "":
                    continue
                if "normalized" in line:
                    continue
                start_position = 0
                for currentColumn in column_names:
                    match = compiled_patterns[currentColumn].search(line[start_position:])

                    if match:
                        if currentColumn not in ("FUNCTION", "B/E", "RESIDUE_VARIETY", "MSA_DATA"):
                            start_position += match.end()
                        if currentColumn == "POS":
                            row[currentColumn] = int(match.group(0))
                        elif currentColumn == "SCORE":
                            row[currentColumn] = float(match.group(0))
                        elif currentColumn == "COLOR":
                            row[currentColumn] = match.group(0)
                        elif currentColumn == "CONFIDENCE_INTERVAL":
                            d = match.group(0).split(",")
                            row["CONFIDENCE_INTERVAL"] = (float(d[0].strip()), float(d[1].strip()))
                        elif currentColumn == "CONFIDENCE_INTERVAL_COLORS":
                            d = match.group(0).split(",")
                            row["CONFIDENCE_INTERVAL_COLORS"] = (d[0].strip(), d[1].strip())
                        elif currentColumn == "RESIDUE_VARIETY":
                            row[currentColumn] = match.group(0).replace(" ", "").split(",")
                        elif currentColumn == "B/E":
                            row["BE"] = match.group(0).strip()
                        else:
                            row[currentColumn] = match.group(0).strip()
                    else:
                        if currentColumn == "B/E":
                            row["BE"] = None
                        else:
                            row[currentColumn] = None
                    if currentColumn == "FUNCTION":
                        data.append(row)

    if len(data) == 0:
        raise ValueError("No data found in file")
    return pd.DataFrame(data)


def read_consurf_msa_variation_file(file_path: str) -> pd.DataFrame:
    column_names = [
        "pos", "A", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "V", "W", "Y", "OTHER", "MAX AA", "ConSurf Grade"
        ]
    df = pd.read_csv(file_path, skiprows=5, names=column_names)
    df["ConSurf Grade"] = df["ConSurf Grade"].astype(str)
    df.rename(columns={"ConSurf Grade": "ConSurf_Grade", "MAX AA": "MAX_AA"}, inplace=True)
    return df
