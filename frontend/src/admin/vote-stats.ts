import { ArcElement, Chart, PieController, Tooltip } from "chart.js";

import { onReady, readJsonScript } from "../lib/dom";

Chart.register(PieController, ArcElement, Tooltip);

interface PieData {
  labels: string[];
  counts: number[];
  colors: string[];
}

onReady(() => {
  const canvas = document.getElementById("pieChart");
  if (!(canvas instanceof HTMLCanvasElement)) return;

  const { labels, counts, colors } = readJsonScript<PieData>("vote-pie-data");
  const total = counts.reduce((sum, value) => sum + value, 0);

  new Chart(canvas, {
    type: "pie",
    data: { labels, datasets: [{ data: counts, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ({ label, raw }) => {
              const value = Number(raw);
              const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : "0";
              return `${label}: ${value} (${percentage}%)`;
            },
          },
        },
      },
    },
  });
});
