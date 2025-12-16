from urllib.parse import urljoin, urlparse
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import asyncio 
import re
import time
import heapq 
from difflib import SequenceMatcher

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_heuristic(link_url, target_url):
   
    link_part = link_url.rstrip('/').split('/')[-1].replace('_', ' ').lower()
    target_part = target_url.rstrip('/').split('/')[-1].replace('_', ' ').lower()
    
   
    return SequenceMatcher(None, link_part, target_part).ratio()

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
                    if re.match(r'^\d+$', link_text) or re.match(r'^\d{4}$', link_text): continue
                    if "Istimewa:" in clean_url or "Bantuan:" in clean_url or "Kategori:" in clean_url: continue
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
    algorithm = data.get("algorithm", "BFS")

    frontier = []
    

    if algorithm in ["UCS", "GREEDY"]:
      
        heapq.heappush(frontier, (0, start_url, 0)) 
    else:
       
        frontier = [(start_url, 0)]

    visited = {start_url}
    parent_map = {start_url: None}

   
    ids_depth_limit = 0
    if algorithm == "IDS":
        
        ids_depth_limit = 1 
    
    
    count = 0
    found = False
    start_time = time.time()

    try:
       
        while (frontier or algorithm == "IDS") and count < max_nodes:
            
       
            if not frontier and algorithm == "IDS":
                ids_depth_limit += 1
                if ids_depth_limit > 10:
                    break
                    
                await websocket.send_json({"type": "status", "msg": f"IDS: Mengulang dengan kedalaman {ids_depth_limit}..."})
                
                frontier = [(start_url, 0)]
               
                visited = {start_url} 
                
                await asyncio.sleep(0.5)
                continue

           
            if algorithm == "BFS":
                current_url, current_depth = frontier.pop(0)
            elif algorithm == "DFS" or algorithm == "IDS":
                current_url, current_depth = frontier.pop() 
            elif algorithm == "UCS":
                cost, current_url, current_depth = heapq.heappop(frontier)
            elif algorithm == "GREEDY":
              
                priority, current_url, current_depth = heapq.heappop(frontier)

            msg_status = f"[{algorithm}] Crawl: {current_url}"
            if algorithm == "IDS": msg_status += f" (Limit: {ids_depth_limit})"
            
            await websocket.send_json({"type": "status", "msg": msg_status})

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
                    break 

                
                if current_depth < 10: 
                    
               
                    if algorithm == "IDS" and current_depth >= ids_depth_limit:
                        continue

                    child_limit = 0
                    for link in page_data['links']:
                       
                        if link not in visited and child_limit < 5: 
                            visited.add(link)
                            parent_map[link] = current_url
                            
                            new_depth = current_depth + 1
                            
                        
                            if algorithm == "UCS":
                           
                                heapq.heappush(frontier, (new_depth, link, new_depth))
                                
                            elif algorithm == "GREEDY":
                            
                                sim_score = calculate_heuristic(link, target_url)
                                priority = 1.0 - sim_score
                                heapq.heappush(frontier, (priority, link, new_depth))
                                
                            else:
                                frontier.append((link, new_depth))
                            
                            child_limit += 1

                      
                            await websocket.send_json({
                                "type": "link_added",
                                "link": {"source": current_url, "target": link}
                            })
                            await asyncio.sleep(0.02) 

            await asyncio.sleep(0.01)

       
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)

        if found:
            path = []
            curr = target_url
           
            while curr is not None and curr in parent_map:
                path.append(curr)
                curr = parent_map[curr]
            
            winning_path = path[::-1]
            await websocket.send_json({
                "type": "path_found", 
                "path": winning_path,
                "time": elapsed_time
            })
            await websocket.send_json({"type": "status", "msg": f"TARGET DITEMUKAN! ({elapsed_time}s)"})
        else:
            await websocket.send_json({
                "type": "status", 
                "msg": f"Gagal/Limit Habis. {count} nodes, {elapsed_time}s."
            })

        await websocket.close()
        
    except Exception as e:
        print(f"Error: {e}")