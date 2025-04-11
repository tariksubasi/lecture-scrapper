import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import json
import tempfile
import os
import schedule
import urllib3


apiUser = {
    "userName": "cereneryigit",
    "password": "fenerbahce2"
}

apiBaseUrl = "http://localhost:8080"
apiEndpointToGetCourses = "/rest/ulug-auth/v1/builder/getSchools-courses-and-lectures"
apiEndpointToAuthenticate = "/rest/ulug-noauth/v1/auth/signin"
apiEndpointToSaveLectureVideos = "/rest/ulug-auth/v1/solver/save-lecture-videos"
apiUrlToGetCourses = apiBaseUrl + apiEndpointToGetCourses
apiUrlToAuthenticate = apiBaseUrl + apiEndpointToAuthenticate
apiUrlToSaveLectureVideos = apiBaseUrl + apiEndpointToSaveLectureVideos

def authenticate():
    """
    API'ye kimlik doğrulama yaparak token alır.
    
    Returns:
        str: Kimlik doğrulama token'ı veya hata durumunda None
    """
    try:
        response = requests.post(apiUrlToAuthenticate, json=apiUser)
        if response.status_code == 200:
            data = response.json()
            print(data.get('accessToken'))
            return data.get('accessToken')
        else:
            print(f"Kimlik doğrulama hatası: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Kimlik doğrulama sırasında hata oluştu: {str(e)}")
        return None

def get_courses_from_api():
    """
    API'den okul, kurs ve ders bilgilerini alır.
    
    Returns:
        list: Okul, kurs ve ders bilgilerini içeren liste veya hata durumunda None
    """
    token = authenticate()
    if not token:
        print("Token alınamadığı için okullar ve kurslar çekilemiyor.")
        return None
    
    try:
        # Postman'deki başarılı isteğe benzer header'lar ekleyelim
        headers = {
            'x-access-token': token,
            'Cookie': f'accessToken={token}',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': 'PythonRequests'
        }
        
        print(f"API isteği gönderiliyor: {apiUrlToGetCourses}")
        print(f"Token: {token}")
        
        response = requests.get(apiUrlToGetCourses, headers=headers)
        
        print(f"API yanıtı: Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Okulları ve kursları alma hatası: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Okulları ve kursları alma sırasında hata oluştu: {str(e)}")
        return None

# Sabit kurs listesi yerine API'den alınan okulları kullan
#schools = get_courses_from_api()

# API'den veri alınamazsa örnek veri kullan
def get_youtube_videos(query, max_results=15):
    """
    YouTube'da belirli bir sorgu için videoları arar, embed edilebilir olanları bulur ve
    izlenme sayısına göre sıralar.
    
    Args:
        query (str): Arama sorgusu
        max_results (int): Döndürülecek maksimum video sayısı
        
    Returns:
        list: Video bilgilerini içeren sözlüklerin listesi
    """
    # Chrome ayarlarını yapılandırma
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Tarayıcıyı görünmez modda çalıştır
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Benzersiz bir kullanıcı veri dizini belirle
    temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_temp_{os.getpid()}")
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Ek ayarlar
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    try:
        # WebDriver'ı başlat
        driver = webdriver.Chrome(options=chrome_options)
        
        # YouTube'un arama sayfasına git ve sorguyu ara (alaka düzeyine göre)
        driver.get("https://www.youtube.com/results?search_query=" + query.replace(" ", "+"))
        # Not: CAMSAhAB parametresini kaldırdık, böylece varsayılan alaka düzeyine göre sıralama kullanılacak
        
        # Sayfanın yüklenmesini bekle
        time.sleep(3)
        
        embeddable_videos = []
        processed_video_ids = set()  # İşlenen video ID'lerini takip etmek için küme
        scroll_count = 0
        min_scrolls = 2  # Minimum kaydırma sayısı
        max_scrolls = 20  # Maksimum kaydırma sayısı
        
        # Döngü koşulu: (Yeterli video YOK VE minimum scroll'a ulaşılmadı) VE maksimum scroll'a ulaşılmadı
        while ((len(embeddable_videos) < max_results and scroll_count < min_scrolls) or scroll_count < max_scrolls):
            # Sayfa içeriğini al
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Video bilgilerini topla
            video_elements = soup.find_all('div', {'id': 'dismissible'})
            
            for element in video_elements:
                # Video başlığını ve ID'sini al
                title_element = element.find('a', {'id': 'video-title'})
                if not title_element:
                    continue
                    
                title = title_element.get('title', '')
                if not title:
                    title = title_element.text.strip()
                    
                video_url = title_element.get('href', '')
                if not video_url or not video_url.startswith('/watch?v='):
                    continue
                    
                video_id = video_url.split('v=')[1].split('&')[0]
                
                # Bu video ID'si zaten kontrol edildi mi?
                if video_id in processed_video_ids:
                    continue
                
                processed_video_ids.add(video_id)  # ID'yi işlenmiş olarak işaretle
                
                # İzlenme sayısını al
                view_count = 0
                
                # Farklı HTML yapılarını kontrol et
                # 1. Yeni YouTube yapısında görüntüleme bilgisi genellikle span içinde bulunur
                view_spans = element.find_all('span', {'class': 'style-scope'})
                for span in view_spans:
                    span_text = span.text.strip()
                    # Görüntüleme sayısı formatlarını kontrol et (1,4 Mn görüntüleme, 1.4M views, 756 B görüntüleme vb.)
                    view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', span_text)
                    if view_match:
                        try:
                            # Önce temel sayıyı al
                            if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                # Türkçe format: 1,4 Mn
                                view_base = float(view_match.group(1).replace(',', '.'))
                            else:
                                # İngilizce format: 1.4M veya düz sayı: 1400
                                view_base = float(view_match.group(1).replace(',', ''))
                            
                            # Çarpanı belirle
                            multiplier = 1
                            if 'B ' in span_text or 'bin' in span_text:
                                multiplier = 1000
                            elif 'K' in span_text:
                                multiplier = 1000
                            elif 'M' in span_text or 'Mn' in span_text or 'milyon' in span_text:
                                multiplier = 1000000
                            elif 'milyar' in span_text:
                                multiplier = 1000000000
                            
                            view_count = int(view_base * multiplier)
                            break
                        except ValueError:
                            continue
                
                # 2. Alternatif olarak aria-label içinde kontrol et
                if view_count == 0:
                    aria_label = title_element.get('aria-label', '')
                    if aria_label:
                        view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', aria_label)
                        if view_match:
                            try:
                                # Önce temel sayıyı al
                                if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                    # Türkçe format: 1,4 Mn
                                    view_base = float(view_match.group(1).replace(',', '.'))
                                else:
                                    # İngilizce format: 1.4M veya düz sayı: 1400
                                    view_base = float(view_match.group(1).replace(',', ''))
                                
                                # Çarpanı belirle
                                multiplier = 1
                                if 'B ' in aria_label or 'bin' in aria_label:
                                    multiplier = 1000
                                elif 'K' in aria_label:
                                    multiplier = 1000
                                elif 'M' in aria_label or 'Mn' in aria_label or 'milyon' in aria_label:
                                    multiplier = 1000000
                                elif 'milyar' in aria_label or 'Mr' in aria_label:
                                    multiplier = 1000000000
                                
                                view_count = int(view_base * multiplier)
                            except ValueError:
                                view_count = 0
                
                # 3. Metadata içinde kontrol et
                if view_count == 0:
                    meta_spans = element.find_all('span', {'class': 'inline-metadata-item'})
                    for span in meta_spans:
                        span_text = span.text.strip()
                        view_match = re.search(r'([\d,.]+)\s*(?:B|K|M|Mn|bin|milyon|milyar)?\s*(?:görüntüleme|views)', span_text)
                        if view_match:
                            try:
                                # Önce temel sayıyı al
                                if ',' in view_match.group(1) and '.' not in view_match.group(1):
                                    # Türkçe format: 1,4 Mn
                                    view_base = float(view_match.group(1).replace(',', '.'))
                                else:
                                    # İngilizce format: 1.4M veya düz sayı: 1400
                                    view_base = float(view_match.group(1).replace(',', ''))
                                
                                # Çarpanı belirle
                                multiplier = 1
                                if 'B ' in span_text or 'bin' in span_text:
                                    multiplier = 1000
                                elif 'K' in span_text:
                                    multiplier = 1000
                                elif 'M' in span_text or 'Mn' in span_text or 'milyon' in span_text:
                                    multiplier = 1000000
                                elif 'milyar' in span_text or 'Mr' in span_text:
                                    multiplier = 1000000000
                                
                                view_count = int(view_base * multiplier)
                                break
                            except ValueError:
                                continue
                
                # Embed edilebilirliği hemen kontrol et
                if check_embeddable(video_id):
                    video_info = {
                        'title': title,
                        'video_id': video_id,
                        'view_count': view_count,
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'watch_url': f'https://www.youtube.com/watch?v={video_id}'
                    }
                    embeddable_videos.append(video_info)
                    print(f"Embed edilebilir video bulundu ({len(embeddable_videos)}/{max_results}): {title}")
            
            # Daha fazla video yüklemek için sayfayı aşağı kaydır
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
            time.sleep(2)
            scroll_count += 1
            print(f"Sayfa kaydırıldı ({scroll_count}/{max_scrolls}), şu ana kadar {len(embeddable_videos)} embed edilebilir video bulundu.")
            
            # Minimum scroll sayısını geçtik ve yeterli video bulduk mu kontrol et
            if scroll_count >= min_scrolls and len(embeddable_videos) >= max_results:
                print(f"Minimum scroll sayısı ({min_scrolls}) aşıldı ve yeterli video ({len(embeddable_videos)}) bulundu. İşlem durduruluyor.")
                break
                
        # Sonuçları izlenme sayısına göre sırala
        embeddable_videos.sort(key=lambda x: x['view_count'], reverse=True)
        return embeddable_videos[:max_results]  # Sadece istenen sayıda video döndür
        
    except Exception as e:
        print(f"WebDriver başlatılırken hata oluştu: {str(e)}")
        return []
        
    finally:
        try:
            driver.quit()
        except:
            pass
        
        # Geçici dizini temizlemeye çalış
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def check_embeddable(video_id):
    """
    Bir videonun embed edilebilir olup olmadığını kontrol eder.
    
    Args:
        video_id (str): YouTube video ID'si
        
    Returns:
        bool: Video embed edilebilirse True, değilse False
    """
    try:
        # Doğrudan embed URL'sine istek at ve durum kodunu kontrol et
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        response = requests.get(embed_url, timeout=5, allow_redirects=True)
        
        # 401 Unauthorized veya diğer hata kodları embed edilemez anlamına gelir
        if response.status_code != 200:
            print(f"Video ID {video_id} embed edilemez. HTTP durum kodu: {response.status_code}")
            return False
            
        # Yanıt içeriğinde "Video unavailable" veya benzeri ifadeler var mı kontrol et
        if "Video unavailable" in response.text or "UNPLAYABLE" in response.text:
            print(f"Video ID {video_id} embed edilemez. İçerik kullanılamıyor.")
            return False
            
        # Ek kontrol: oEmbed API'sini de kullan
        oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        oembed_response = requests.get(oembed_url, timeout=5)
        
        if oembed_response.status_code != 200:
            print(f"Video ID {video_id} için oEmbed API hatası: {oembed_response.status_code}")
            return False
            
        return True
    except Exception as e:
        print(f"Video ID {video_id} embed kontrolü sırasında hata: {str(e)}")
        return False

def get_lecture_videos(schools, max_results_per_lecture=10):
    """
    Tüm okullar, kurslar ve dersler için YouTube videoları arar ve sonuçları toplar.
    
    Args:
        schools (list): Okul, kurs ve ders bilgilerini içeren liste
        max_results_per_lecture (int): Her ders için aranacak maksimum video sayısı
        
    Returns:
        list: Ders videoları listesi
    """
    lecture_video_list = []
    
    for school in schools:
        school_type = school.get("schoolType", "")
        
        for course in school["Courses"]:
            course_name = course["courseName"]
            
            for lecture in course["Lectures"]:
                lecture_id = lecture["lectureId"]
                lecture_name = lecture["lectureName"]
                
                # Arama sorgusu oluştur - okul tipini de ekleyebiliriz
                query = f"{school_type} - {course_name} - {lecture_name}"
                print(f"\nArama yapılıyor: {query}")
                
                # YouTube'da ara
                videos = get_youtube_videos(query, max_results=max_results_per_lecture)
                
                # Sonuçları listeye ekle
                for video in videos:
                    video_info = {
                        "lectureId": lecture_id,
                        "videoName": video["title"],
                        "youtubeVideoID": video["video_id"],
                        "url": video["watch_url"],
                        "embedUrl": video["embed_url"],
                        "viewCount": video["view_count"]
                    }
                    lecture_video_list.append(video_info)
                    
                print(f"{lecture_name} için {len(videos)} video bulundu.")
    
    return lecture_video_list

def save_lecture_videos_to_api(lecture_videos):
    """
    Hazırlanan ders videolarını API'ye kaydeder.
    
    Args:
        lecture_videos (list): Kaydedilecek ders videoları listesi
        
    Returns:
        bool: İşlem başarılıysa True, değilse False
    """
    token = authenticate()
    if not token:
        print("Token alınamadığı için videolar kaydedilemiyor.")
        return False
    
    try:
        # Postman'deki başarılı isteğe benzer header'lar ekleyelim
        headers = {
            'x-access-token': token,
            'Cookie': f'accessToken={token}',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': 'PythonRequests'
        }
        
        print(f"API isteği gönderiliyor: {apiUrlToSaveLectureVideos}")
        print(f"Kaydedilecek video sayısı: {len(lecture_videos)}")
        
        response = requests.post(apiUrlToSaveLectureVideos, json=lecture_videos, headers=headers)
        
        print(f"API yanıtı: Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"API yanıtı: {response.json()}")
            return True
        else:
            print(f"Video kaydetme hatası: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Video kaydetme sırasında hata oluştu: {str(e)}")
        return False

if __name__ == "__main__":
    # SSL uyarılarını devre dışı bırak (geliştirme ortamı için)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def job():
        print(f"YouTube video arama işlemi başlatılıyor... {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Her çalıştırmada okulları yeniden al (token yenilemek için)
        current_schools = get_courses_from_api()
        
        if not current_schools:
            print("Okullar alınamadı, işlem iptal ediliyor.")
            return
        
        # Tüm okullar ve dersler için YouTube videoları aranıyor
        print("Tüm okullar ve dersler için YouTube videoları aranıyor...")
        
        # Her ders için en fazla 10 video ara
        lecture_videos = get_lecture_videos(current_schools, max_results_per_lecture=10)
        
        # Sonuçları göster
        print(f"\nToplam {len(lecture_videos)} video bulundu.")
        
        # Sonuçları API'ye kaydet
        if lecture_videos:
            save_result = save_lecture_videos_to_api(lecture_videos)
            if save_result:
                print("Videolar başarıyla API'ye kaydedildi.")
            else:
                print("Videoların API'ye kaydedilmesi sırasında bir hata oluştu.")
        
        # İsteğe bağlı: Sonuçları JSON olarak kaydet
        with open("lecture_videos.json", "w", encoding="utf-8") as f:
            json.dump(lecture_videos, f, ensure_ascii=False, indent=2)
        
        print("Sonuçlar lecture_videos.json dosyasına kaydedildi.")
        print(f"İşlem tamamlandı. {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Her gün saat 02:00'de çalıştır
    schedule.every().day.at("02:21").do(job)
    
    print(f"YouTube video arama servisi başlatıldı. {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Her gün saat 02:21'de otomatik olarak çalışacak.")
    
    # İlk çalıştırma için kontrol et
    if time.localtime().tm_hour == 2 and time.localtime().tm_min == 21:
        print("Başlangıç saati ile eşleşme sağlandı, hemen çalıştırılıyor...")
        job()
    
    # Sonsuz döngü ile zamanlayıcıyı kontrol et
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Her dakika kontrol et
        except KeyboardInterrupt:
            print("Program kullanıcı tarafından durduruldu.")
            break
        except Exception as e:
            print(f"Beklenmeyen bir hata oluştu: {str(e)}")
            # Hata durumunda 5 dakika bekle ve tekrar dene
            time.sleep(300)
