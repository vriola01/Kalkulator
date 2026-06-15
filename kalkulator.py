import streamlit as st
import pdfplumber
import re
import math
from functools import reduce

# --- FUNKCJE MATEMATYCZNE ---
def oblicz_wielkosc_pakietu(ilosci_na_palecie, grubosc_plyty):
    if not ilosci_na_palecie or grubosc_plyty <= 0:
        return 1
    nwd_ogolne = reduce(math.gcd, ilosci_na_palecie)
    dzielniki = []
    for i in range(1, nwd_ogolne + 1):
        if nwd_ogolne % i == 0:
            dzielniki.append(i)
    dzielniki.sort(reverse=True)
    for dzielnik in dzielniki:
        if dzielnik * grubosc_plyty <= 150:
            return dzielnik
    return 1

# --- SILNIK (BACKEND) ---
def wyciagnij_dane_z_pdf(wczytany_plik):
    caly_tekst = ""
    tekst_podsumowania = ""
    try:
        with pdfplumber.open(wczytany_plik) as pdf:
            for strona in pdf.pages:
                tekst_strony = strona.extract_text()
                if tekst_strony:
                    caly_tekst += tekst_strony + "\n"
                    
                    # --- INTELIGENTNE FILTROWANIE STRON ---
                    # Lista nagłówków tabel pomocniczych, które dublują nasze dane
                    niechciane_strony = [
                        "Plan sztaplowania", 
                        "Przegląd planów cięcia", 
                        "Protokół pakowania", 
                        "Przegląd płyt ochronnych"
                    ]
                    
                    # Jeśli na stronie NIE MA żadnego z tych nagłówków, to znaczy, 
                    # że mamy przed sobą idealnie czystą stronę podsumowania (z naszą tabelą).
                    czy_to_detale = any(znacznik in tekst_strony for znacznik in niechciane_strony)
                    if not czy_to_detale:
                        tekst_podsumowania += tekst_strony + "\n"
                        
        # 1. Płyty Wsadowe (szukamy TYLKO na odfiltrowanych stronach podsumowania)
        wzorzec_tabeli = re.findall(r'(?m)^\s*(?:\d{1,3}\s+)?(\d{3,4})\s+(\d{3,4})\s+(\d+\.\d+)\s+(\d{1,5})\b', tekst_podsumowania)
        
        # 2. Formatki - wyciągamy kolumnę "II. rzecz." (szukamy TYLKO na stronach podsumowania)
        wzorzec_formatek = re.findall(r'(?m)^\s*(?:\d{1,3}\s+)?\d{3,4}\s+\d{3,4}\s+(?:[a-zA-Z0-9-]+\s+)?\d+\s+(\d+)\b', tekst_podsumowania)
        
        # 3. Układanie / Pakietowanie (szukamy w CAŁYM pliku, bo może być tylko na "Protokole pakowania")
        wzorzec_ukladania = re.findall(r'(\d{2,4})\s*,\s*\d{3,5}\s*,\s*[a-zA-Z0-9]', caly_tekst)
        
        ilosci_paletowe_tekst = "250"
        if wzorzec_ukladania:
            unikalne_ilosci = set([int(x) for x in wzorzec_ukladania])
            ilosci_paletowe_lista = sorted(list(unikalne_ilosci), reverse=True)
            ilosci_paletowe_tekst = ", ".join(str(x) for x in ilosci_paletowe_lista)

        calkowita_objetosc = 0.0
        calkowita_liczba_plyt = 0 
        zidentyfikowane_formaty = []
        znaleziona_grubosc = 0.0
        laczna_ilosc_formatek = 0

        # Sumowanie płyt
        if wzorzec_tabeli:
            for dlugosc_str, szerokosc_str, grubosc_str, ilosc_str in wzorzec_tabeli:
                dlugosc = float(dlugosc_str)
                szerokosc = float(szerokosc_str)
                grubosc = float(grubosc_str)
                ilosc = int(ilosc_str)

                objetosc_partii = (dlugosc * szerokosc * grubosc * ilosc) / 1_000_000_000
                calkowita_objetosc += objetosc_partii
                calkowita_liczba_plyt += ilosc 
                znaleziona_grubosc = grubosc

                zidentyfikowane_formaty.append(f"{ilosc} szt. | {dlugosc_str} x {szerokosc_str} x {grubosc_str} mm")

        # Sumowanie formatek
        if wzorzec_formatek:
            laczna_ilosc_formatek = sum(int(x) for x in wzorzec_formatek)

        return {
            "objetosc": round(calkowita_objetosc, 3),
            "liczba_plyt": calkowita_liczba_plyt,
            "grubosc": znaleziona_grubosc,
            "formaty": "\n".join(zidentyfikowane_formaty) if zidentyfikowane_formaty else "Brak zidentyfikowanych partii.",
            "ilosci_paletowe": ilosci_paletowe_tekst,
            "ilosc_formatek": laczna_ilosc_formatek,
            "sukces": True
        }
    except Exception as e:
        return {"sukces": False, "blad": str(e)}

# --- INTERFEJS WEBOWY (FRONTEND) ---
st.set_page_config(page_title="Kalkulator HDF", layout="wide")
st.title("Kalkulator Czasu i Kosztu Cięcia HDF")

kolumna_lewa, kolumna_prawa = st.columns([1, 1.2])

with kolumna_lewa:
    st.subheader("1. Parametry Maszyny")
    wydajnosc = st.number_input("Wydajność bazowa (m3/h):", min_value=0.1, value=12.0, step=0.1)
    koszt_pracy = st.number_input("Koszt pracy maszyny (PLN/h):", min_value=0.0, value=672.0, step=10.0)
    powierzchnia_wzorcowa = st.number_input("Powierzchnia płyty wzorcowej (m2):", value=9.68, step=0.1)

    st.subheader("2. Wczytaj Plik pCut")
    plik_pdf = st.file_uploader("Przeciągnij plik PDF tutaj", type=["pdf"])

with kolumna_prawa:
    st.subheader("3. Dane Zlecenia i Wyniki")
    
    if plik_pdf is not None:
        dane = wyciagnij_dane_z_pdf(plik_pdf)
        
        if dane["sukces"]:
            kol_dane1, kol_dane2 = st.columns(2)
            
            with kol_dane1:
                objetosc_edytowana = st.number_input("Rzeczywista objętość (m3):", value=float(dane["objetosc"]), format="%.3f")
                liczba_plyt_edytowana = st.number_input("Liczba płyt wsadowych (szt):", value=int(dane["liczba_plyt"]), step=1)
                grubosc_edytowana = st.number_input("Grubość płyty (mm):", value=float(dane["grubosc"]), format="%.1f")
                
            with kol_dane2:
                # TUTAJ JEST KLUCZOWA ZMIANA - podpinamy odczytaną zmienną z silnika!
                ilosc_formatek = st.number_input("Łączna ilość formatek (szt):", value=int(dane["ilosc_formatek"]), step=10)
                ilosci_tekst = st.text_input("Ilości na palecie (po przecinku):", value=dane["ilosci_paletowe"])
                
            st.text_area("Zidentyfikowane formaty:", value=dane["formaty"], height=100)
            
            st.markdown("---")
            
            try:
                lista_ilosci = [int(x.strip()) for x in ilosci_tekst.split(",") if x.strip().isdigit()]
                wyliczony_pakiet = oblicz_wielkosc_pakietu(lista_ilosci, grubosc_edytowana)

                st.markdown("#### Podsumowanie Zlecenia")
                wynik1, wynik2, wynik3, wynik4 = st.columns(4)
                
                with wynik1:
                    ostateczny_pakiet = st.number_input("📦 Pakiet (szt):", value=int(wyliczony_pakiet), step=1)
                
                if wydajnosc > 0 and liczba_plyt_edytowana > 0 and ostateczny_pakiet > 0 and grubosc_edytowana > 0:
                    
                    stopien_skomplikowania = ilosc_formatek / liczba_plyt_edytowana
                    
                    # --- NOWA, PRECYZYJNA SKALA MNOŻNIKA 'KN' ---
                    if stopien_skomplikowania > 12:
                        kn = 2.0
                    elif stopien_skomplikowania >= 11: # Próg 11-12
                        kn = 1.8
                    elif stopien_skomplikowania >= 9:  # Próg 9-10
                        kn = 1.6
                    elif stopien_skomplikowania >= 7:  # Próg 7-8
                        kn = 1.4
                    elif stopien_skomplikowania >= 5:  # Próg 5-6
                        kn = 1.2
                    elif stopien_skomplikowania >= 3:  # Próg 3-4
                        kn = 1.0
                    else:                              # Próg 1-2
                        kn = 0.8
                        
                    calkowita_powierzchnia = objetosc_edytowana / (grubosc_edytowana / 1000)
                    srednia_pow_plyt = calkowita_powierzchnia / liczba_plyt_edytowana

                    czesc_1 = objetosc_edytowana / wydajnosc
                    czesc_2_pierwiastek = (powierzchnia_wzorcowa / srednia_pow_plyt) ** (1/3)
                    
                    # --- ZAAWANSOWANE WYKORZYSTANIE WYSOKOŚCI CIĘCIA (150 mm) ---
                    # Wysokość rzeczywista pakietu = ostateczny_pakiet * grubosc_edytowana
                    czesc_3_pakiet = 150 / (ostateczny_pakiet * grubosc_edytowana)
                    
                    czas_calkowity = czesc_1 * (czesc_2_pierwiastek * czesc_3_pakiet * kn)
                    koszt_calkowity = czas_calkowity * koszt_pracy
                    
                    wynik2.metric(label="🧩 Formatek/Płytę", value=f"{stopien_skomplikowania:.1f}")
                    wynik3.metric(label="⏱️ Szacowany Czas", value=f"{czas_calkowity:.2f} h")
                    wynik4.metric(label="💰 Szacowany Koszt", value=f"{koszt_calkowity:.2f} PLN")
                    
            except Exception as e:
                st.error("Błąd obliczeń. Upewnij się, że wprowadzone dane są poprawne.")
                
        else:
            st.error(f"Wystąpił błąd podczas analizy pliku: {dane['blad']}")
    else:
        st.info("Czekam na wczytanie pliku PDF...")
