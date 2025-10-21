import re
import pandas as pd
import zipfile
import os
import tempfile

def read_consurf_grade_from_zip(zip_path, grade_filename=None):
    """
    Extract and read consurf_grades.txt file from a zip archive

    Parameters:
    zip_path (str): Path to the zip file
    grade_filename (str, optional): Specific filename to look for. If None, will look for
                                   any file ending with '_consurf_grades.txt'

    Returns:
    pd.DataFrame: DataFrame containing the parsed consurf grades
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Find the consurf grades file
        if grade_filename is None:
            # Look for any file ending with _consurf_grades.txt
            for file in zip_ref.namelist():
                if file.endswith('_consurf_grades.txt') or file == 'no_model_consurf_grades.txt':
                    grade_filename = file
                    break

            if grade_filename is None:
                raise FileNotFoundError("No consurf grades file found in the zip archive")

        # Create a temporary file to extract to
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # Extract the file to the temporary location
        zip_ref.extract(grade_filename, path=os.path.dirname(temp_path))
        extracted_path = os.path.join(os.path.dirname(temp_path), grade_filename)

        try:
            # Read the extracted file
            df = read_consurf_grade_file_new(extracted_path)
            return df
        finally:
            # Clean up the temporary file
            if os.path.exists(extracted_path):
                os.remove(extracted_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)

def read_consurf_grade_file_new(file_path: str) -> pd.DataFrame:
    column_names = [
        'POS', 'SEQ', 'ATOM', 'SCORE', 'COLOR', 'CONFIDENCE_INTERVAL', 'CONFIDENCE_INTERVAL_COLORS',
        'B/E', 'FUNCTION', 'MSA_DATA', 'RESIDUE_VARIETY'
    ]
    patterns = {
        'POS': r'\d+',
        'SEQ': r'[A-Z]',
        'ATOM': r'[A-Z]{3}\d+[A-Z]?',
        'SCORE': r'-?\d+\.\d{1,3}',
        'COLOR': r'\d',
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
                if "SCORE" in line and "COLOR" in line and "CONFIDENCE INTERVAL" in line:
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
                            row[currentColumn] = [int(match.group(0))]
                        elif currentColumn == "CONFIDENCE_INTERVAL":
                            d = match.group(0).split(",")
                            row["CONFIDENCE_INTERVAL"] = (float(d[0].strip()), float(d[1].strip()))
                        elif currentColumn == "CONFIDENCE_INTERVAL_COLORS":
                            d = match.group(0).split(",")
                            row["CONFIDENCE_INTERVAL_COLORS"] = (d[0].strip(), d[1].strip())
                        elif currentColumn == "RESIDUE_VARIETY":
                            row[currentColumn] = match.group(0).replace(" ", "").split(",")
                        elif currentColumn == "MSA_DATA":
                            row[currentColumn] = [int(i) for i in match.group(0).split("/") if i != ""]
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
                        elif currentColumn == "MSA_DATA":
                            row[currentColumn] = [int(i) for i in match.group(0).split("/") if i != ""]
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
    for c in column_names:
        if c not in ("pos", "MAX AA", "ConSurf Grade"):
            df[c] = df[c].fillna(0)
    df["ConSurf Grade"] = df["ConSurf Grade"].astype(str)
    df.rename(columns={"ConSurf Grade": "ConSurf_Grade", "MAX AA": "MAX_AA"}, inplace=True)
    return df

def get_all_pdb_chains(file_path: str) -> list[str]:
    results = []
    with open(file_path, "rt") as f:
        for line in f:
            line = line.strip()
            if line[:4] == "ATOM" or line[:6] == "HETATM":
                results.append(line[21])
    return list(set(results))

def get_all_sequence_names_from_alignment(file_path: str) -> list[str]:
    results = []
    with open(file_path, "rt") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                results.append(line[1:].split(" ")[0])

    return list(set(results))