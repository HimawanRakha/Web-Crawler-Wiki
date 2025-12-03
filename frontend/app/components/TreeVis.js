"use client";
import React from "react";
import Tree from "react-d3-tree";

const renderCustomNode = ({ nodeDatum, toggleNode }) => {
  const fullTitle = nodeDatum.name || "No Title";
  const label = fullTitle.length > 15 ? fullTitle.substring(0, 15) + "..." : fullTitle;

  const isWinner = nodeDatum.attributes?.isWinner;

  const nodeColor = isWinner ? "green" : "white";
  const nodeRadius = isWinner ? 20 : 20;
  const textColor = isWinner ? "green" : "black";

  return (
    <g>
      <circle
        r={nodeRadius}
        fill={nodeColor}
        strokeWidth="1"
        onClick={toggleNode}
        style={{ transition: "all 0.5s ease" }}
      />

      <text fill={textColor} x="0" y={isWinner ? "36" : "31"} textAnchor="middle" fontSize={isWinner ? "18px" : "18px"} fontWeight="regular">
        {label}
      </text>
    </g>
  );
};

const TreeVis = ({ treeData }) => {
  if (!treeData || Object.keys(treeData).length === 0) {
    return (
      <div className="w-full h-[500px] border border-gray-800 rounded-xl bg-black flex flex-col items-center justify-center text-gray-500 gap-2">
        <p className="text-xl"></p>
        <p>Masukkan Start & Target URL untuk memulai</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "700px", background: "white" }} className="rounded-xl border border-white overflow-hidden shadow-2xl shadow-red-900/20">
      <Tree
        data={treeData}
        orientation="vertical"
        pathFunc="straight"
        translate={{ x: 600, y: 50 }}
        renderCustomNodeElement={renderCustomNode}
        zoomable={true}
        scaleExtent={{ min: 0.1, max: 2 }}
        styles={{
          links: {
            stroke: "white",
            strokeWidth: 1,
            strokeOpacity: 0.5,
          },
        }}
      />
    </div>
  );
};

export default TreeVis;
