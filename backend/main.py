from urllib.parse import urljoin, urlparse
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import asyncio 
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_page_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Educational Project)'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')

        title = "No Title"
        if soup.title: title = soup.title.text.strip()
        elif soup.find('h1'): title = soup.find('h1').text.strip()
        
        links = []
        base_domain = urlparse(url).netloc

        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(url, a_tag['href'])
            parsed = urlparse(full_url)

            if parsed.scheme in ['http', 'https'] and parsed.netloc == base_domain:
                 if not any(full_url.endswith(ext) for ext in ['.png', '.jpg', '.pdf', '.svg']):
                    clean_url = full_url.split('#')[0]

                    link_text = a_tag.text.strip()
                    if re.match(r'^\d+$', link_text) or re.match(r'^\d{4}$', link_text):
                        continue

                    if "Istimewa:" in clean_url or "Bantuan:" in clean_url or "Kategori:" in clean_url:
                        continue

                    links.append(clean_url)
        
        return {"title": title, "links": list(set(links))}
    except:
        return None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    data = await websocket.receive_json()
    start_url = data.get("start_url")
    target_url = data.get("target_url")
    max_nodes = data.get("max_nodes", 100)

    queue = [(start_url, 0)] 
    visited = {start_url}
    parent_map = {start_url: None}

    count = 0
    found = False

    try:
        while queue and count < max_nodes:
            current_url, current_depth = queue.pop(0) 

            await websocket.send_json({"type": "status", "msg": f"Crawl: {current_url} (Layer {current_depth})"})

            page_data = get_page_data(current_url)

            if page_data:
                await websocket.send_json({
                    "type": "node_added",
                    "node": {
                        "id": current_url,
                        "title": page_data['title'],
                        "depth": current_depth
                    }
                })
                
                count += 1

                if target_url in page_data['links']:
                    parent_map[target_url] = current_url
                    found = True

                    target_data = get_page_data(target_url)
                    await websocket.send_json({
                        "type": "node_added",
                        "node": {
                            "id": target_url,
                            "title": target_data['title'] if target_data else "TARGET",
                            "depth": current_depth + 1
                        }
                    })
                    await websocket.send_json({
                        "type": "link_added",
                        "link": {"source": current_url, "target": target_url}
                    })

                    await websocket.send_json({"type": "status", "msg": "TARGET DITEMUKAN!"})
                    break

                if current_depth < 6:
                    child_limit = 0
                    for link in page_data['links']:
                        if link not in visited and child_limit < 4: 
                            visited.add(link)
                            parent_map[link] = current_url
                            queue.append((link, current_depth + 1))
                            child_limit += 1

                            await websocket.send_json({
                                "type": "link_added",
                                "link": {"source": current_url, "target": link}
                            })
                            await asyncio.sleep(0.05) 

            await asyncio.sleep(0.01)

        if found:
            path = []
            curr = target_url
            while curr is not None:
                path.append(curr)
                curr = parent_map.get(curr)
            
            winning_path = path[::-1]
            await websocket.send_json({"type": "path_found", "path": winning_path})
        else:
            await websocket.send_json({"type": "status", "msg": f"Gagal. Sudah {count} node tapi belum ketemu."})

        await websocket.close()
        
    except Exception as e:
        print(f"Error: {e}")