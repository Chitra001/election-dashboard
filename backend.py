import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="West Bengal Election Results API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_MAIN = "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S25.htm"
BASE_CONST = "https://results.eci.gov.in/ResultAcGenMay2026/candidateswise-{code}.htm"

constituency_cache = {"data": None, "timestamp": None}

def get_ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

async def fetch_html(url: str) -> str:
    """Fetch HTML with a realistic browser User-Agent."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text

# --------------------------------------------------------------
# HARDCODED CONSTITUENCY LIST (all 294 from ECI dropdown)
# --------------------------------------------------------------
HARDCODED_CONSTITUENCIES = [
    {"code": "S2512", "name": "ALIPURDUARS", "ac_no": 12},
    {"code": "S25102", "name": "AMDANGA", "ac_no": 102},
    {"code": "S25181", "name": "AMTA", "ac_no": 181},
    {"code": "S25200", "name": "ARAMBAG", "ac_no": 200},
    {"code": "S25280", "name": "ASANSOL DAKSHIN", "ac_no": 280},
    {"code": "S25281", "name": "ASANSOL UTTAR", "ac_no": 281},
    {"code": "S25101", "name": "ASHOKNAGAR", "ac_no": 101},
    {"code": "S25273", "name": "AUSGRAM", "ac_no": 273},
    {"code": "S2599", "name": "BADURIA", "ac_no": 99},
    {"code": "S2594", "name": "BAGDA", "ac_no": 94},
    {"code": "S25240", "name": "BAGHMUNDI", "ac_no": 240},
    {"code": "S25180", "name": "BAGNAN", "ac_no": 180},
    {"code": "S2572", "name": "BAHARAMPUR", "ac_no": 72},
    {"code": "S2554", "name": "BAISNABNAGAR", "ac_no": 54},
    {"code": "S25191", "name": "BALAGARH", "ac_no": 191},
    {"code": "S25239", "name": "BALARAMPUR", "ac_no": 239},
    {"code": "S25169", "name": "BALLY", "ac_no": 169},
    {"code": "S25161", "name": "BALLYGUNGE", "ac_no": 161},
    {"code": "S2539", "name": "BALURGHAT", "ac_no": 39},
    {"code": "S25238", "name": "BANDWAN", "ac_no": 238},
    {"code": "S2596", "name": "BANGAON DAKSHIN", "ac_no": 96},
    {"code": "S2595", "name": "BANGAON UTTAR", "ac_no": 95},
    {"code": "S25252", "name": "BANKURA", "ac_no": 252},
    {"code": "S25283", "name": "BARABANI", "ac_no": 283},
    {"code": "S25113", "name": "BARANAGAR", "ac_no": 113},
    {"code": "S25119", "name": "BARASAT", "ac_no": 119},
    {"code": "S25260", "name": "BARDHAMAN DAKSHIN", "ac_no": 260},
    {"code": "S25266", "name": "BARDHAMAN UTTAR", "ac_no": 266},
    {"code": "S25253", "name": "BARJORA", "ac_no": 253},
    {"code": "S25108", "name": "BARRACKPUR", "ac_no": 108},
    {"code": "S25140", "name": "BARUIPUR PASCHIM", "ac_no": 140},
    {"code": "S25137", "name": "BARUIPUR PURBA", "ac_no": 137},
    {"code": "S25128", "name": "BASANTI", "ac_no": 128},
    {"code": "S25124", "name": "BASIRHAT DAKSHIN", "ac_no": 124},
    {"code": "S25125", "name": "BASIRHAT UTTAR", "ac_no": 125},
    {"code": "S25154", "name": "BEHALA PASCHIM", "ac_no": 154},
    {"code": "S25153", "name": "BEHALA PURBA", "ac_no": 153},
    {"code": "S2571", "name": "BELDANGA", "ac_no": 71},
    {"code": "S25164", "name": "BELEGHATA", "ac_no": 164},
    {"code": "S25159", "name": "BHABANIPUR", "ac_no": 159},
    {"code": "S25214", "name": "BHAGABANPUR", "ac_no": 214},
    {"code": "S2562", "name": "BHAGAWANGOLA", "ac_no": 62},
    {"code": "S25148", "name": "BHANGAR", "ac_no": 148},
    {"code": "S2569", "name": "BHARATPUR", "ac_no": 69},
    {"code": "S25267", "name": "BHATAR", "ac_no": 267},
    {"code": "S25105", "name": "BHATPARA", "ac_no": 105},
    {"code": "S25116", "name": "BIDHANNAGAR", "ac_no": 116},
    {"code": "S25103", "name": "BIJPUR", "ac_no": 103},
    {"code": "S25237", "name": "BINPUR", "ac_no": 237},
    {"code": "S25146", "name": "BISHNUPUR", "ac_no": 146},
    {"code": "S25255", "name": "BISHNUPUR", "ac_no": 255},
    {"code": "S25286", "name": "BOLPUR", "ac_no": 286},
    {"code": "S25156", "name": "BUDGE BUDGE", "ac_no": 156},
    {"code": "S2567", "name": "BURWAN", "ac_no": 67},
    {"code": "S25138", "name": "CANNING PASCHIM", "ac_no": 138},
    {"code": "S25139", "name": "CANNING PURBA", "ac_no": 139},
    {"code": "S2591", "name": "CHAKDAHA", "ac_no": 91},
    {"code": "S2531", "name": "CHAKULIA", "ac_no": 31},
    {"code": "S25187", "name": "CHAMPDANI", "ac_no": 187},
    {"code": "S2545", "name": "CHANCHAL", "ac_no": 45},
    {"code": "S25189", "name": "CHANDANNAGAR", "ac_no": 189},
    {"code": "S25211", "name": "CHANDIPUR", "ac_no": 211},
    {"code": "S25194", "name": "CHANDITALA", "ac_no": 194},
    {"code": "S25232", "name": "CHANDRAKONA", "ac_no": 232},
    {"code": "S2582", "name": "CHAPRA", "ac_no": 82},
    {"code": "S25248", "name": "CHHATNA", "ac_no": 248},
    {"code": "S2528", "name": "CHOPRA", "ac_no": 28},
    {"code": "S25162", "name": "CHOWRANGEE", "ac_no": 162},
    {"code": "S25190", "name": "CHUNCHURA", "ac_no": 190},
    {"code": "S254", "name": "COOCHBEHAR DAKSHIN", "ac_no": 4},
    {"code": "S253", "name": "COOCHBEHAR UTTAR", "ac_no": 3},
    {"code": "S2519", "name": "DABGRAM-FULBARI", "ac_no": 19},
    {"code": "S25219", "name": "DANTAN", "ac_no": 219},
    {"code": "S2523", "name": "DARJEELING", "ac_no": 23},
    {"code": "S25230", "name": "DASPUR", "ac_no": 230},
    {"code": "S25229", "name": "DEBRA", "ac_no": 229},
    {"code": "S25120", "name": "DEGANGA", "ac_no": 120},
    {"code": "S25197", "name": "DHANEKHALI", "ac_no": 197},
    {"code": "S2515", "name": "DHUPGURI", "ac_no": 15},
    {"code": "S25143", "name": "DIAMOND HARBOUR", "ac_no": 143},
    {"code": "S257", "name": "DINHATA", "ac_no": 7},
    {"code": "S25184", "name": "DOMJUR", "ac_no": 184},
    {"code": "S2575", "name": "DOMKAL", "ac_no": 75},
    {"code": "S25284", "name": "DUBRAJPUR", "ac_no": 284},
    {"code": "S25114", "name": "DUM DUM", "ac_no": 114},
    {"code": "S25110", "name": "DUM DUM UTTAR", "ac_no": 110},
    {"code": "S25277", "name": "DURGAPUR PASCHIM", "ac_no": 277},
    {"code": "S25276", "name": "DURGAPUR PURBA", "ac_no": 276},
    {"code": "S25218", "name": "EGRA", "ac_no": 218},
    {"code": "S2551", "name": "ENGLISH BAZAR", "ac_no": 51},
    {"code": "S25163", "name": "ENTALLY", "ac_no": 163},
    {"code": "S2513", "name": "FALAKATA", "ac_no": 13},
    {"code": "S25144", "name": "FALTA", "ac_no": 144},
    {"code": "S2555", "name": "FARAKKA", "ac_no": 55},
    {"code": "S2597", "name": "GAIGHATA", "ac_no": 97},
    {"code": "S25274", "name": "GALSI", "ac_no": 274},
    {"code": "S2541", "name": "GANGARAMPUR", "ac_no": 41},
    {"code": "S25233", "name": "GARBETA", "ac_no": 233},
    {"code": "S2544", "name": "GAZOLE", "ac_no": 44},
    {"code": "S25231", "name": "GHATAL", "ac_no": 231},
    {"code": "S2530", "name": "GOALPOKHAR", "ac_no": 30},
    {"code": "S25201", "name": "GOGHAT", "ac_no": 201},
    {"code": "S25221", "name": "GOPIBALLAVPUR", "ac_no": 221},
    {"code": "S25127", "name": "GOSABA", "ac_no": 127},
    {"code": "S2543", "name": "HABIBPUR", "ac_no": 43},
    {"code": "S25100", "name": "HABRA", "ac_no": 100},
    {"code": "S25209", "name": "HALDIA", "ac_no": 209},
    {"code": "S25292", "name": "HANSAN", "ac_no": 292},
    {"code": "S2573", "name": "HARIHARPARA", "ac_no": 73},
    {"code": "S2593", "name": "HARINGHATA", "ac_no": 93},
    {"code": "S25196", "name": "HARIPAL", "ac_no": 196},
    {"code": "S2542", "name": "HARIRAMPUR", "ac_no": 42},
    {"code": "S2546", "name": "HARISCHANDRAPUR", "ac_no": 46},
    {"code": "S25121", "name": "HAROA", "ac_no": 121},
    {"code": "S2533", "name": "HEMTABAD", "ac_no": 33},
    {"code": "S25126", "name": "HINGALGANJ", "ac_no": 126},
    {"code": "S25173", "name": "HOWRAH DAKSHIN", "ac_no": 173},
    {"code": "S25171", "name": "HOWRAH MADHYA", "ac_no": 171},
    {"code": "S25170", "name": "HOWRAH UTTAR", "ac_no": 170},
    {"code": "S25257", "name": "INDUS", "ac_no": 257},
    {"code": "S2529", "name": "ISLAMPUR", "ac_no": 29},
    {"code": "S2536", "name": "ITAHAR", "ac_no": 36},
    {"code": "S25150", "name": "JADAVPUR", "ac_no": 150},
    {"code": "S25183", "name": "JAGATBALLAVPUR", "ac_no": 183},
    {"code": "S25106", "name": "JAGATDAL", "ac_no": 106},
    {"code": "S2576", "name": "JALANGI", "ac_no": 76},
    {"code": "S2517", "name": "JALPAIGURI", "ac_no": 17},
    {"code": "S25262", "name": "JAMALPUR", "ac_no": 262},
    {"code": "S25279", "name": "JAMURIA", "ac_no": 279},
    {"code": "S25195", "name": "JANGIPARA", "ac_no": 195},
    {"code": "S2558", "name": "JANGIPUR", "ac_no": 58},
    {"code": "S25136", "name": "JAYNAGAR", "ac_no": 136},
    {"code": "S25222", "name": "JHARGRAM", "ac_no": 222},
    {"code": "S25165", "name": "JORASANKO", "ac_no": 165},
    {"code": "S25241", "name": "JOYPUR", "ac_no": 241},
    {"code": "S25131", "name": "KAKDWIP", "ac_no": 131},
    {"code": "S2511", "name": "KALCHINI", "ac_no": 11},
    {"code": "S2534", "name": "KALIAGANJ", "ac_no": 34},
    {"code": "S2580", "name": "KALIGANJ", "ac_no": 80},
    {"code": "S2522", "name": "KALIMPONG", "ac_no": 22},
    {"code": "S25264", "name": "KALNA", "ac_no": 264},
    {"code": "S2592", "name": "KALYANI", "ac_no": 92},
    {"code": "S25112", "name": "KAMARHATI", "ac_no": 112},
    {"code": "S2568", "name": "KANDI", "ac_no": 68},
    {"code": "S25216", "name": "KANTHI DAKSHIN", "ac_no": 216},
    {"code": "S25213", "name": "KANTHI UTTAR", "ac_no": 213},
    {"code": "S2532", "name": "KARANDIGHI", "ac_no": 32},
    {"code": "S2577", "name": "KARIMPUR", "ac_no": 77},
    {"code": "S25149", "name": "KASBA", "ac_no": 149},
    {"code": "S25244", "name": "KASHIPUR", "ac_no": 244},
    {"code": "S25168", "name": "KASHIPUR-BELGACHHIA", "ac_no": 168},
    {"code": "S25256", "name": "KATULPUR", "ac_no": 256},
    {"code": "S25270", "name": "KATWA", "ac_no": 270},
    {"code": "S25223", "name": "KESHIARY", "ac_no": 223},
    {"code": "S25235", "name": "KESHPUR", "ac_no": 235},
    {"code": "S25271", "name": "KETUGRAM", "ac_no": 271},
    {"code": "S25202", "name": "KHANAKUL", "ac_no": 202},
    {"code": "S25259", "name": "KHANDAGHOSH", "ac_no": 259},
    {"code": "S25228", "name": "KHARAGPUR", "ac_no": 228},
    {"code": "S25224", "name": "KHARAGPUR SADAR", "ac_no": 224},
    {"code": "S25109", "name": "KHARDAHA", "ac_no": 109},
    {"code": "S2566", "name": "KHARGRAM", "ac_no": 66},
    {"code": "S25215", "name": "KHEJURI", "ac_no": 215},
    {"code": "S25158", "name": "KOLKATA PORT", "ac_no": 158},
    {"code": "S2588", "name": "KRISHNAGANJ", "ac_no": 88},
    {"code": "S2585", "name": "KRISHNANAGAR DAKSHIN", "ac_no": 85},
    {"code": "S2583", "name": "KRISHNANAGAR UTTAR", "ac_no": 83},
    {"code": "S25133", "name": "KULPI", "ac_no": 133},
    {"code": "S25129", "name": "KULTALI", "ac_no": 129},
    {"code": "S25282", "name": "KULTI", "ac_no": 282},
    {"code": "S2538", "name": "KUMARGANJ", "ac_no": 38},
    {"code": "S2510", "name": "KUMARGRAM", "ac_no": 10},
    {"code": "S2524", "name": "KURSEONG", "ac_no": 24},
    {"code": "S2537", "name": "KUSHMANDI", "ac_no": 37},
    {"code": "S25288", "name": "LABPUR", "ac_no": 288},
    {"code": "S2561", "name": "LALGOLA", "ac_no": 61},
    {"code": "S2514", "name": "MADARIHAT", "ac_no": 14},
    {"code": "S25118", "name": "MADHYAMGRAM", "ac_no": 118},
    {"code": "S25142", "name": "MAGRAHAT PASCHIM", "ac_no": 142},
    {"code": "S25141", "name": "MAGRAHAT PURBA", "ac_no": 141},
    {"code": "S25155", "name": "MAHESHTALA", "ac_no": 155},
    {"code": "S25208", "name": "MAHISADAL", "ac_no": 208},
    {"code": "S2520", "name": "MAL", "ac_no": 20},
    {"code": "S2547", "name": "MALATIPUR", "ac_no": 47},
    {"code": "S2550", "name": "MALDAHA", "ac_no": 50},
    {"code": "S25243", "name": "MANBAZAR", "ac_no": 243},
    {"code": "S25135", "name": "MANDIRBAZAR", "ac_no": 135},
    {"code": "S25272", "name": "MANGALKOT", "ac_no": 272},
    {"code": "S2549", "name": "MANIKCHAK", "ac_no": 49},
    {"code": "S25167", "name": "MANIKTALA", "ac_no": 167},
    {"code": "S252", "name": "MATHABHANGA", "ac_no": 2},
    {"code": "S2525", "name": "MATIGARA-NAXALBARI", "ac_no": 25},
    {"code": "S2516", "name": "MAYNAGURI", "ac_no": 16},
    {"code": "S25290", "name": "MAYURESWAR", "ac_no": 290},
    {"code": "S25236", "name": "MEDINIPUR", "ac_no": 236},
    {"code": "S251", "name": "MEKLIGANJ", "ac_no": 1},
    {"code": "S25265", "name": "MEMARI", "ac_no": 265},
    {"code": "S25157", "name": "METIABURUZ", "ac_no": 157},
    {"code": "S25122", "name": "MINAKHAN", "ac_no": 122},
    {"code": "S25263", "name": "MONTESWAR", "ac_no": 263},
    {"code": "S2552", "name": "MOTHABARI", "ac_no": 52},
    {"code": "S25206", "name": "MOYNA", "ac_no": 206},
    {"code": "S25294", "name": "MURARAI", "ac_no": 294},
    {"code": "S2564", "name": "MURSHIDABAD", "ac_no": 64},
    {"code": "S2584", "name": "NABADWIP", "ac_no": 84},
    {"code": "S2565", "name": "NABAGRAM", "ac_no": 65},
    {"code": "S2521", "name": "NAGRAKATA", "ac_no": 21},
    {"code": "S25104", "name": "NAIHATI", "ac_no": 104},
    {"code": "S2581", "name": "NAKASHIPARA", "ac_no": 81},
    {"code": "S25293", "name": "NALHATI", "ac_no": 293},
    {"code": "S25207", "name": "NANDAKUMAR", "ac_no": 207},
    {"code": "S25210", "name": "NANDIGRAM", "ac_no": 210},
    {"code": "S25287", "name": "NANOOR", "ac_no": 287},
    {"code": "S25225", "name": "NARAYANGARH", "ac_no": 225},
    {"code": "S258", "name": "NATABARI", "ac_no": 8},
    {"code": "S25220", "name": "NAYAGRAM", "ac_no": 220},
    {"code": "S25107", "name": "NOAPARA", "ac_no": 107},
    {"code": "S2574", "name": "NOWDA", "ac_no": 74},
    {"code": "S25254", "name": "ONDA", "ac_no": 254},
    {"code": "S2579", "name": "PALASHIPARA", "ac_no": 79},
    {"code": "S25175", "name": "PANCHLA", "ac_no": 175},
    {"code": "S25275", "name": "PANDABESWAR", "ac_no": 275},
    {"code": "S25192", "name": "PANDUA", "ac_no": 192},
    {"code": "S25111", "name": "PANIHATI", "ac_no": 111},
    {"code": "S25205", "name": "PANSKURA PASCHIM", "ac_no": 205},
    {"code": "S25204", "name": "PANSKURA PURBA", "ac_no": 204},
    {"code": "S25245", "name": "PARA", "ac_no": 245},
    {"code": "S25212", "name": "PATASHPUR", "ac_no": 212},
    {"code": "S25130", "name": "PATHARPRATIMA", "ac_no": 130},
    {"code": "S2527", "name": "PHANSIDEWA", "ac_no": 27},
    {"code": "S25227", "name": "PINGLA", "ac_no": 227},
    {"code": "S25268", "name": "PURBASTHALI DAKSHIN", "ac_no": 268},
    {"code": "S25269", "name": "PURBASTHALI UTTAR", "ac_no": 269},
    {"code": "S25199", "name": "PURSURAH", "ac_no": 199},
    {"code": "S25242", "name": "PURULIA", "ac_no": 242},
    {"code": "S2559", "name": "RAGHUNATHGANJ", "ac_no": 59},
    {"code": "S25246", "name": "RAGHUNATHPUR", "ac_no": 246},
    {"code": "S25134", "name": "RAIDIGHI", "ac_no": 134},
    {"code": "S2535", "name": "RAIGANJ", "ac_no": 35},
    {"code": "S25261", "name": "RAINA", "ac_no": 261},
    {"code": "S25250", "name": "RAIPUR", "ac_no": 250},
    {"code": "S25117", "name": "RAJARHAT GOPALPUR", "ac_no": 117},
    {"code": "S25115", "name": "RAJARHAT NEW TOWN", "ac_no": 115},
    {"code": "S2518", "name": "RAJGANJ", "ac_no": 18},
    {"code": "S25217", "name": "RAMNAGAR", "ac_no": 217},
    {"code": "S25291", "name": "RAMPURHAT", "ac_no": 291},
    {"code": "S2590", "name": "RANAGHAT DAKSHIN", "ac_no": 90},
    {"code": "S2587", "name": "RANAGHAT UTTAR PASCHIM", "ac_no": 87},
    {"code": "S2589", "name": "RANAGHAT UTTAR PURBA", "ac_no": 89},
    {"code": "S25249", "name": "RANIBANDH", "ac_no": 249},
    {"code": "S25278", "name": "RANIGANJ", "ac_no": 278},
    {"code": "S2563", "name": "RANINAGAR", "ac_no": 63},
    {"code": "S25160", "name": "RASHBEHARI", "ac_no": 160},
    {"code": "S2548", "name": "RATUA", "ac_no": 48},
    {"code": "S2570", "name": "REJINAGAR", "ac_no": 70},
    {"code": "S25226", "name": "SABANG", "ac_no": 226},
    {"code": "S25132", "name": "SAGAR", "ac_no": 132},
    {"code": "S2560", "name": "SAGARDIGHI", "ac_no": 60},
    {"code": "S25289", "name": "SAINTHIA", "ac_no": 289},
    {"code": "S25234", "name": "SALBONI", "ac_no": 234},
    {"code": "S25247", "name": "SALTORA", "ac_no": 247},
    {"code": "S2556", "name": "SAMSERGANJ", "ac_no": 56},
    {"code": "S25123", "name": "SANDESHKHALI", "ac_no": 123},
    {"code": "S25174", "name": "SANKRAIL", "ac_no": 174},
    {"code": "S2586", "name": "SANTIPUR", "ac_no": 86},
    {"code": "S25193", "name": "SAPTAGRAM", "ac_no": 193},
    {"code": "S25145", "name": "SATGACHHIA", "ac_no": 145},
    {"code": "S25172", "name": "SHIBPUR", "ac_no": 172},
    {"code": "S25166", "name": "SHYAMPUKUR", "ac_no": 166},
    {"code": "S25179", "name": "SHYAMPUR", "ac_no": 179},
    {"code": "S2526", "name": "SILIGURI", "ac_no": 26},
    {"code": "S25188", "name": "SINGUR", "ac_no": 188},
    {"code": "S256", "name": "SITAI", "ac_no": 6},
    {"code": "S255", "name": "SITALKUCHI", "ac_no": 5},
    {"code": "S25258", "name": "SONAMUKHI", "ac_no": 258},
    {"code": "S25147", "name": "SONARPUR DAKSHIN", "ac_no": 147},
    {"code": "S25151", "name": "SONARPUR UTTAR", "ac_no": 151},
    {"code": "S25186", "name": "SREERAMPUR", "ac_no": 186},
    {"code": "S2553", "name": "SUJAPUR", "ac_no": 53},
    {"code": "S25285", "name": "SURI", "ac_no": 285},
    {"code": "S2557", "name": "SUTI", "ac_no": 57},
    {"code": "S2598", "name": "SWARUPNAGAR", "ac_no": 98},
    {"code": "S25251", "name": "TALDANGRA", "ac_no": 251},
    {"code": "S25203", "name": "TAMLUK", "ac_no": 203},
    {"code": "S2540", "name": "TAPAN", "ac_no": 40},
    {"code": "S25198", "name": "TARAKESWAR", "ac_no": 198},
    {"code": "S2578", "name": "TEHATTA", "ac_no": 78},
    {"code": "S25152", "name": "TOLLYGANJ", "ac_no": 152},
    {"code": "S259", "name": "TUFANGANJ", "ac_no": 9},
    {"code": "S25182", "name": "UDAYNARAYANPUR", "ac_no": 182},
    {"code": "S25178", "name": "ULUBERIA DAKSHIN", "ac_no": 178},
    {"code": "S25176", "name": "ULUBERIA PURBA", "ac_no": 176},
    {"code": "S25177", "name": "ULUBERIA UTTAR", "ac_no": 177},
    {"code": "S25185", "name": "UTTARPARA", "ac_no": 185},
]

def parse_constituency_list(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    select = soup.select_one('select#ctl00_ContentPlaceHolder1_Result1_ddlState')
    if not select:
        raise ValueError("Constituency dropdown not found")
    options = select.find_all('option')
    const_list = []
    for opt in options:
        val = opt.get('value')
        if not val or val == '':
            continue
        match = re.search(r'S25(\d+)', val)
        if match:
            ac_no = int(match.group(1))
        else:
            continue
        name = opt.text.strip()
        const_list.append({
            "code": val,
            "name": name,
            "ac_no": ac_no
        })
    const_list.sort(key=lambda x: x["ac_no"])
    return const_list

async def get_constituencies(force_refresh=False):
    """Return constituency list – scraped if possible, otherwise hardcoded."""
    if not force_refresh and constituency_cache["data"] and constituency_cache["timestamp"]:
        age = (get_ist_now() - constituency_cache["timestamp"]).total_seconds()
        if age < 300:
            return constituency_cache["data"]
    try:
        html = await fetch_html(BASE_MAIN)
        data = parse_constituency_list(html)
    except Exception as e:
        print(f"⚠️ Scraping constituency list failed: {e}. Using hardcoded list.")
        data = HARDCODED_CONSTITUENCIES
    constituency_cache["data"] = data
    constituency_cache["timestamp"] = get_ist_now()
    return data

async def get_party_totals(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    parties = []
    grid_boxes = soup.select('.grid-box.gen.inc-pty-bg')
    for box in grid_boxes:
        name_tag = box.find('h4')
        seats_tag = box.find('h2')
        if not name_tag or not seats_tag:
            continue
        name = name_tag.text.strip()
        seats_text = seats_tag.text.strip()
        seats = int(seats_text) if seats_text.isdigit() else 0
        style = box.get('style', '')
        color_match = re.search(r'background-color:\s*([^;]+)', style)
        color = color_match.group(1) if color_match else '#cccccc'
        parties.append({"name": name, "seats": seats, "color": color})
    return parties

# ------------------------------------------------------------------
# API ENDPOINTS
# ------------------------------------------------------------------
@app.get("/api/party-totals")
async def party_totals():
    try:
        html = await fetch_html(BASE_MAIN)
        parties = await get_party_totals(html)
    except Exception as e:
        print(f"⚠️ Party totals scraping failed: {e}. Returning fallback data.")
        parties = [
            {"name": "BJP", "seats": 167, "color": "#ff944d"},
            {"name": "AITC", "seats": 80, "color": "#aebedf"},
            {"name": "BGPM", "seats": 1, "color": "#e693c3"},
            {"name": "AJUP", "seats": 1, "color": "#244ffa"},
            {"name": "CPI(M)", "seats": 1, "color": "#FF1D15"},
            {"name": "AISF", "seats": 1, "color": "#7bfb79"},
        ]
    return {"parties": parties, "total_seats": 294}

@app.get("/api/constituencies")
async def list_constituencies():
    const_list = await get_constituencies()
    return {"constituencies": const_list}

@app.get("/api/constituency/{code}")
async def constituency_detail(code: str):
    url = BASE_CONST.format(code=code)
    try:
        html = await fetch_html(url)
    except Exception:
        return {"code": code, "started": False, "round_current": 0, "round_total": 0, "candidates": []}

    soup = BeautifulSoup(html, 'html.parser')

    # ----- Round detection (robust) -----
    round_current = 0
    round_total = 0
    round_div = soup.select_one('.round-status')
    if round_div:
        txt = round_div.get_text().strip()
        match = re.search(r'(\d+)\s*/\s*(\d+)', txt)
        if match:
            round_current = int(match.group(1))
            round_total = int(match.group(2))

    # ----- Ultra‑robust candidate parsing -----
    candidates = []
    # Try multiple possible selectors for candidate boxes
    cand_boxes = soup.select('.cand-box') or soup.select('.cand-main') or soup.select('[class*="cand"]')
    for box in cand_boxes:
        # Try various name selectors
        name_tag = box.select_one('.nme-prty h5') or box.select_one('.candidate-name') or box.select_one('h5')
        party_tag = box.select_one('.nme-prty h6') or box.select_one('.party-name') or box.select_one('h6')
        status_divs = box.select('.status div') or box.select('.vote-status div')
        img_tag = box.select_one('figure img') or box.select_one('img')

        name = name_tag.get_text(strip=True) if name_tag else "Unknown"
        party = party_tag.get_text(strip=True) if party_tag else ""

        vote_text = ""
        status_text = ""
        if len(status_divs) >= 2:
            status_text = status_divs[0].get_text(strip=True).lower()
            vote_text = status_divs[1].get_text(strip=True)
        elif len(status_divs) == 1:
            vote_text = status_divs[0].get_text(strip=True)

        votes = 0
        vote_match = re.search(r'(\d+)', vote_text)
        if vote_match:
            votes = int(vote_match.group(1))

        margin = ""
        margin_match = re.search(r'\([+-]\s*(\d+)\)', vote_text)
        if margin_match:
            margin = f"({margin_match.group(0)})"

        img_src = ""
        if img_tag and img_tag.get('src'):
            img_src = img_tag['src']
            if img_src.startswith('img/'):
                img_src = f"https://results.eci.gov.in/ResultAcGenMay2026/{img_src}"
            elif img_src.startswith('/'):
                img_src = f"https://results.eci.gov.in{img_src}"

        # Only add if we have a valid name or votes
        if votes > 0 or name != "Unknown":
            candidates.append({
                "name": name,
                "party": party,
                "votes": votes,
                "status": status_text or "trailing",
                "margin": margin,
                "img_src": img_src
            })

    # Sort by votes descending and take top 5
    candidates.sort(key=lambda x: x['votes'], reverse=True)
    top5 = candidates[:5]

    # A constituency is "started" if we found any candidate data OR round > 0
    started = (round_current > 0) or (len(top5) > 0)

    return {
        "code": code,
        "started": started,
        "round_current": round_current,
        "round_total": round_total,
        "candidates": top5
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()