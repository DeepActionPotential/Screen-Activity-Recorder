from dataclasses import dataclass



from dataclasses import dataclass
from typing import Optional


@dataclass
class RecordingConfig:
    # General
    enable_keyboard: bool = True
    enable_mouse: bool = True
    enable_screenshot: bool = False
    enable_application_tracking: bool = True

    # Intervals & thresholds
    screenshot_interval_seconds: int = 10  # Capture screen every X seconds
    app_poll_interval_seconds: int = 5     # Check active window every X seconds
    idle_threshold_seconds: int = 60       # Consider user idle after X seconds

    # # Performance tuning
    # compress_screenshots: bool = True          # Reduce screenshot size





@dataclass
class LLMConfig:
        
    model_name:str = "gemini-2.0-flash"
    api_key: str = "your-api-key"

    keywords_extraction_prompt:str = "Extract the main keywords that describe this text, on that format: keyword1, keyword2, keyword3, ...."


@dataclass
class EmbeddingConfig:

    embedding_model_name: str = 'all-MiniLM-L6-v2'
    embedding_dim: int = 512
    embedding_device: str = 'cpu'


@dataclass
class NERConfig:
    model_path = "./models/NER_BILSTM_CRF.pt"



@dataclass
class TokenizerConfig:
    

    
    tokenizer_name = "bert-base-uncased"
    max_len: int = 512
    non_senstive_label2id = {
        "O": 110,
    }
    
    label2id = {'B-ACCOUNTNAME': 0,
                'B-ACCOUNTNUMBER': 1,
                'B-AGE': 2,
                'B-AMOUNT': 3,
                'B-BIC': 4,
                'B-BITCOINADDRESS': 5,
                'B-BUILDINGNUMBER': 6,
                'B-CITY': 7,
                'B-COMPANYNAME': 8,
                'B-COUNTY': 9,
                'B-CREDITCARDCVV': 10,
                'B-CREDITCARDISSUER': 11,
                'B-CREDITCARDNUMBER': 12,
                'B-CURRENCY': 13,
                'B-CURRENCYCODE': 14,
                'B-CURRENCYNAME': 15,
                'B-CURRENCYSYMBOL': 16,
                'B-DATE': 17,
                'B-DOB': 18,
                'B-EMAIL': 19,
                'B-ETHEREUMADDRESS': 20,
                'B-EYECOLOR': 21,
                'B-FIRSTNAME': 22,
                'B-GENDER': 23,
                'B-HEIGHT': 24,
                'B-IBAN': 25,
                'B-IP': 26,
                'B-IPV4': 27,
                'B-IPV6': 28,
                'B-JOBAREA': 29,
                'B-JOBTITLE': 30,
                'B-JOBTYPE': 31,
                'B-LASTNAME': 32,
                'B-LITECOINADDRESS': 33,
                'B-MAC': 34,
                'B-MASKEDNUMBER': 35,
                'B-MIDDLENAME': 36,
                'B-NEARBYGPSCOORDINATE': 37,
                'B-ORDINALDIRECTION': 38,
                'B-PASSWORD': 39,
                'B-PHONEIMEI': 40,
                'B-PHONENUMBER': 41,
                'B-PIN': 42,
                'B-PREFIX': 43,
                'B-SECONDARYADDRESS': 44,
                'B-SEX': 45,
                'B-SSN': 46,
                'B-STATE': 47,
                'B-STREET': 48,
                'B-TIME': 49,
                'B-URL': 50,
                'B-USERAGENT': 51,
                'B-USERNAME': 52,
                'B-VEHICLEVIN': 53,
                'B-VEHICLEVRM': 54,
                'B-ZIPCODE': 55,
                'I-ACCOUNTNAME': 56,
                'I-ACCOUNTNUMBER': 57,
                'I-AGE': 58,
                'I-AMOUNT': 59,
                'I-BIC': 60,
                'I-BITCOINADDRESS': 61,
                'I-BUILDINGNUMBER': 62,
                'I-CITY': 63,
                'I-COMPANYNAME': 64,
                'I-COUNTY': 65,
                'I-CREDITCARDCVV': 66,
                'I-CREDITCARDISSUER': 67,
                'I-CREDITCARDNUMBER': 68,
                'I-CURRENCY': 69,
                'I-CURRENCYCODE': 70,
                'I-CURRENCYNAME': 71,
                'I-CURRENCYSYMBOL': 72,
                'I-DATE': 73,
                'I-DOB': 74,
                'I-EMAIL': 75,
                'I-ETHEREUMADDRESS': 76,
                'I-EYECOLOR': 77,
                'I-FIRSTNAME': 78,
                'I-GENDER': 79,
                'I-HEIGHT': 80,
                'I-IBAN': 81,
                'I-IP': 82,
                'I-IPV4': 83,
                'I-IPV6': 84,
                'I-JOBAREA': 85,
                'I-JOBTITLE': 86,
                'I-JOBTYPE': 87,
                'I-LASTNAME': 88,
                'I-LITECOINADDRESS': 89,
                'I-MAC': 90,
                'I-MASKEDNUMBER': 91,
                'I-MIDDLENAME': 92,
                'I-NEARBYGPSCOORDINATE': 93,
                'I-PASSWORD': 94,
                'I-PHONEIMEI': 95,
                'I-PHONENUMBER': 96,
                'I-PIN': 97,
                'I-PREFIX': 98,
                'I-SECONDARYADDRESS': 99,
                'I-SSN': 100,
                'I-STATE': 101,
                'I-STREET': 102,
                'I-TIME': 103,
                'I-URL': 104,
                'I-USERAGENT': 105,
                'I-USERNAME': 106,
                'I-VEHICLEVIN': 107,
                'I-VEHICLEVRM': 108,
                'I-ZIPCODE': 109,
                'O': 110
                }