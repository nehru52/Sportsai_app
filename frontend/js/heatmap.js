/**
 * Renders a spatial heatmap on a canvas element.
 * @param {string} trackId - The player's track ID.
 */
async function renderHeatmap(trackId) {
    const canvas = document.getElementById(`canvas-${trackId}`);
    const peakText = document.getElementById(`peak-${trackId}`);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const cw = canvas.width = 400;
    const ch = canvas.height = 240;

    try {
        const resp = await fetch(`http://localhost:8000/api/players/${trackId}/heatmap`);
        const heatmap = await resp.json();

        const rows = heatmap.grid_rows;
        const cols = heatmap.grid_cols;
        const data = heatmap.data;
        const cellW = cw / cols;
        const cellH = ch / rows;

        // Find max for normalization
        let maxVal = 0;
        data.forEach(row => row.forEach(val => { if(val > maxVal) maxVal = val; }));

        // 1. Draw Heatmap Cells
        for (let r = 0; r < rows; r++) {
            for (let c = 0; r < rows && c < cols; c++) {
                const val = data[r][c];
                if (val > 0) {
                    const alpha = maxVal > 0 ? val / maxVal : 0;
                    ctx.fillStyle = `rgba(77, 140, 255, ${alpha})`; // Blue gradient
                    ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
                }
            }
        }

        // 2. Draw Court Outline Overlay
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, cw, ch); // Border

        // Centre line
        ctx.beginPath();
        ctx.moveTo(cw / 2, 0);
        ctx.lineTo(cw / 2, ch);
        ctx.stroke();

        // Attack lines (at 1/3 and 2/3)
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(cw / 3, 0); ctx.lineTo(cw / 3, ch);
        ctx.moveTo(2 * cw / 3, 0); ctx.lineTo(2 * cw / 3, ch);
        ctx.stroke();
        ctx.setLineDash([]);

        if (peakText) peakText.innerText = `Peak Activity: ${heatmap.peak_zone.toUpperCase()}`;

    } catch (e) {
        console.error(e);
        ctx.fillStyle = '#5c5c8a';
        ctx.textAlign = 'center';
        ctx.fillText('No heatmap data available', cw/2, ch/2);
    }
}

window.renderHeatmap = renderHeatmap;
