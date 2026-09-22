import { useEffect, useRef } from "react";
import * as d3 from "d3";

export default function IdentityGraph({
  nodes = [],
  edges = [],
}) {
  const svgRef = useRef(null);

  useEffect(() => {

    const width = 800;
    const height = 450;

    const svg = d3
      .select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`);

    svg.selectAll("*").remove();

    if (!nodes.length) return;

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(140)
      )
      .force(
        "charge",
        d3.forceManyBody().strength(-300)
      )
      .force(
        "center",
        d3.forceCenter(
          width / 2,
          height / 2
        )
      );

    const link = svg
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", "#dc2626")
      .attr(
        "stroke-width",
        (d) => 1 + d.similarity * 3
      );

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr(
        "r",
        (d) =>
          d.type === "face" ? 24 : 17
      )
      .attr(
        "fill",
        (d) =>
          d.type === "face"
            ? "#1f4e78"
            : "#d97706"
      );

    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.label)
      .attr("font-size", 12)
      .attr("fill", "#333")
      .attr("text-anchor", "middle");

    simulation.on("tick", () => {

      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node
        .attr("cx", (d) => d.x)
        .attr("cy", (d) => d.y);

      label
        .attr("x", (d) => d.x)
        .attr("y", (d) => d.y - 30);

    });

    return () => {
      simulation.stop();
    };

  }, [nodes, edges]);

  return (
    <div className="bg-white rounded-xl shadow p-4 overflow-hidden">

      <svg
        ref={svgRef}
        className="w-full"
      />

    </div>
  );
}