"use client";
import { useState, useRef, useEffect } from "react";
import TreeVis from "./components/TreeVis";

export default function Home() {
  const [startUrl, setStartUrl] = useState("https://id.wikipedia.org/wiki/Soekarno");
  const [targetUrl, setTargetUrl] = useState("https://id.wikipedia.org/wiki/Barack_Obama");

  const [rawData, setRawData] = useState({ nodes: [], links: [] });
  const [treeStructure, setTreeStructure] = useState({});
  const [winningPath, setWinningPath] = useState([]);

  const [status, setStatus] = useState("Siap mencari jalur...");
  const [isCrawling, setIsCrawling] = useState(false);
  const ws = useRef(null);

  function buildTree(nodes, links, pathArray) {
    if (nodes.length === 0) return {};

    const dataMap = {};
    nodes.forEach((node) => {
      const isWinner = pathArray.includes(node.id);

      dataMap[node.id] = {
        name: node.title,
        attributes: {
          url: node.id,
          depth: node.depth,
          isWinner: isWinner,
        },
        children: [],
      };
    });

    let rootNode = null;

    links.forEach((link) => {
      const parent = dataMap[link.source];
      const child = dataMap[link.target];
      if (parent && child) {
        parent.children.push(child);
      }
    });

    // Cari root (biasanya node pertama di array rawData atau depth 0)
    if (nodes.length > 0) {
      // Kita cari node yang depth-nya 0
      const root = nodes.find((n) => n.depth === 0);
      if (root) rootNode = dataMap[root.id];
    }

    return rootNode || {};
  }

  useEffect(() => {
    if (rawData.nodes.length > 0) {
      const nestedTree = buildTree(rawData.nodes, rawData.links, winningPath);
      setTreeStructure(nestedTree);
    }
  }, [rawData, winningPath]);

  const startCrawl = () => {
    setRawData({ nodes: [], links: [] });
    setWinningPath([]);
    setTreeStructure({});
    setIsCrawling(true);
    setStatus("Menghubungkan...");

    if (ws.current) ws.current.close();

    ws.current = new WebSocket("ws://127.0.0.1:8000/ws");

    ws.current.onopen = () => {
      setStatus("Terhubung! Mencari Target...");
      ws.current.send(
        JSON.stringify({
          start_url: startUrl,
          target_url: targetUrl,
          max_nodes: 100,
        })
      );
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "status") {
        setStatus(data.msg);
      } else if (data.type === "node_added") {
        setRawData((prev) => ({ ...prev, nodes: [...prev.nodes, data.node] }));
      } else if (data.type === "link_added") {
        setRawData((prev) => ({ ...prev, links: [...prev.links, data.link] }));
      } else if (data.type === "path_found") {
        setWinningPath(data.path);
        setStatus(`Jalur Ditemukan! Panjang adalah ${data.path.length} langkah.`);
      }
    };

    ws.current.onclose = () => {
      setIsCrawling(false);
    };
  };

  const nodesByLayer = rawData.nodes.reduce((acc, node) => {
    const depth = node.depth || 0;
    if (!acc[depth]) acc[depth] = [];
    acc[depth].push(node);
    return acc;
  }, {});

  return (
    <main className="flex min-h-screen flex-col items-center p-8 bg-black text-white font-sans">
      <h1 className="text-4xl font-extrabold mb-8 tracking-tight border-b-2 border-white pb-2">Wikipedia Path Finder</h1>

      <div className="flex flex-col md:flex-row gap-4 w-full max-w-4xl mb-6">
        <div className="flex-1">
          <label className="text-xs text-gray-400 ml-1">Start URL</label>
          <input type="text" value={startUrl} onChange={(e) => setStartUrl(e.target.value)} className="w-full p-3 rounded border border-white bg-gray-900 text-white focus:outline-none focus:border-green-500" />
        </div>

        <div className="flex items-center justify-center pt-5">
          <span className="text-md">ke</span>
        </div>

        <div className="flex-1">
          <label className="text-xs text-gray-400 ml-1">Target URL</label>
          <input type="text" value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} className="w-full p-3 rounded border border-white bg-gray-900 text-white focus:outline-none focus:border-red-500" />
        </div>

        <button onClick={startCrawl} disabled={isCrawling} className={`mt-5 px-6 py-3 font-bold rounded transition-all ${isCrawling ? "bg-gray-700 text-gray-500" : "bg-green-600 hover:bg-green-500 text-white"}`}>
          {isCrawling ? "Mencari..." : "CARI JALUR"}
        </button>
      </div>

      <p className={`mb-4 text-sm font-mono ${winningPath.length > 0 ? "text-green-400 font-bold text-lg" : "text-gray-400"}`}>{status}</p>

      <div className="w-full max-w-7xl mb-12">
        <TreeVis treeData={treeStructure} />
      </div>

      {Object.keys(nodesByLayer).length > 0 && (
        <div className="w-full max-w-6xl mt-8 animate-fade-in-up">
          <h2 className="text-2xl font-bold mb-6 border-l-4 border-white pl-4">Laporan & Statistik</h2>

          <div className="space-y-8">
            {Object.keys(nodesByLayer)
              .sort((a, b) => a - b)
              .map((layer) => (
                <div key={layer} className="relative">
                  <div className="sticky top-0 bg-black z-10 py-2 mb-2 flex items-center gap-4">
                    <div className="bg-white text-black font-bold px-3 py-1 rounded-full text-sm shadow-white shadow-sm">Layer {layer}</div>
                    <div className="text-xs text-gray-500">{nodesByLayer[layer].length} Halaman</div>
                    <div className="h-px bg-gray-800 flex-1"></div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                    {nodesByLayer[layer].map((node, idx) => {
                      const isWinner = winningPath.includes(node.id);

                      return (
                        <div
                          key={idx}
                          className={`
                                p-3 rounded border transition-all duration-300
                                ${isWinner ? "border-green-500 bg-green-900/30 scale-105" : "border-gray-800 bg-gray-900/50 hover:border-gray-500"}
                            `}
                        >
                          <h3 className={`font-bold mb-1 truncate text-sm ${isWinner ? "text-green-400" : "text-gray-200"}`} title={node.title}>
                            {node.title || "No Title"}
                          </h3>

                          {isWinner && <span className="inline-block bg-green-600 text-white text-[10px] px-1.5 py-0.5 rounded mb-2">PART OF PATH</span>}

                          <a href={node.id} target="_blank" rel="noreferrer" className="block text-xs text-gray-500 hover:text-white truncate">
                            {node.id}
                          </a>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </main>
  );
}
