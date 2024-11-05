import pandas as pd
import xml.etree.ElementTree as ET
import json

def read_dataset(file,extension):
    try:
        
        if extension == "csv":
            try:
                df = pd.read_csv(file)
                print(df)
            except Exception as e:
                return {"Error" : f"Error Reading CSV file: {str(e)}"}
            
       
        elif extension in ["xls", "xlsx", "xlsm", "xlsb"]:  
                                
            '''to read xlsb files we need to install pyxlsb
               to read xls files we need to install openpyxl and xlrd''' 
            try:               
                df = pd.read_excel(file)
                
            except Exception as e:
                return {"Error" : f"Error Reading Excel file: {str(e)}"}

        
        elif extension =="json":
            try:
                json_data = json.loads(file.read())
                if isinstance(json_data, list):
                    df = pd.DataFrame(json_data)
                elif isinstance(json_data, dict):
                    if "data" in json_data:
                        df = pd.DataFrame(json_data["data"])
                    elif "table" in json_data:
                        df = pd.DataFrame(json_data["table"]["rows"], columns=json_data["table"]["headers"])
                    else:
                        return {"Error" :"Unsupported JSON Data format"}
                else:
                    return {"Error" :"Unsupported JSON structure"}
            except json.JSONDecodeError as e:
                return {"Error" :f"Error decoding JSON file: {str(e)}"}
            except KeyError as e:
                return {"Error" :f"Error accessing JSON keys: {str(e)}"}
            except Exception as e:
                return {"Error" : f"Error processing JSON file: {str(e)}"}
            
               
        elif extension == "parquet":
            try:
                df = pd.read_parquet(file) 
                return df 
            except Exception as e:
                return {'Error': f'Error reading Parquet file: {str(e)}'}
            
        
        elif extension == "xml":
            try:
                tree = ET.parse(file)
                root = tree.getroot()
                data = []
                for child in root:
                    record = {}
                    for subchild in child:
                        record[subchild.tag] = subchild.text
                    data.append(record)
                df = pd.DataFrame(data)
            except FileNotFoundError as e:
                return {'Error': f'File not found: {str(e)}'}
            except ET.ParseError as e:
                return {'Error': f'Error parsing XML file: {str(e)}'}
            except Exception as e:
                return {'Error': f'Error reading XML file: {str(e)}'}
        
        elif extension == "html":
            try:
                
                html_content = file.read().decode("utf-8")  
                df_list = pd.read_html(html_content)
                if df_list:
                    df = pd.concat(df_list, ignore_index=True)
                else:
                    return {"Error" :f"Error decoding HTML file"}
            except FileNotFoundError:
                return {'Error': 'File not found'}
            except PermissionError:
                return {'Error': 'Permission denied'}
            except Exception as e:
                return {'Error': f'Error processing HTML file: {str(e)}'}
                
        else:
            return {'Error': f'Unsupported file type: {extension}'}
        return df
        
    except Exception as e:
        return {'Error': f'Unable to fetch File path: {str(e)}'}
