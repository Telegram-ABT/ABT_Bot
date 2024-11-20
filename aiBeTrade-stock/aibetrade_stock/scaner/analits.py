import requests
from bs4 import BeautifulSoup

def find_analit(ticker):
    analit = get_stock_metrics(ticker)
    print(analit)

def get_stock_metrics(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}:NASDAQ"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Ошибка при доступе к странице: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Поиск значения P/E
    pe_ratio_element = soup.find('div', text='P/E ratio')
    if pe_ratio_element:
        pe_ratio = pe_ratio_element.find_next_sibling('div').text
    else:
        pe_ratio = 'N/A'

    # Поиск значения EPS
    eps_element = soup.find('div', text='Earnings per share')
    if eps_element:
        eps = eps_element.find_next_sibling('div').text
    else:
        eps = 'N/A'

    return {'P/E Ratio': pe_ratio, 'EPS': eps}

if __name__ == "__main__":
    find_analit("AAPL:NASDAQ")