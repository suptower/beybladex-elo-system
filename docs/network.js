// network.js – Interactive Beyblade Mindmap / Relationship Graph
// Uses vis-network (bundled locally as vis-network.min.js) for force-directed graph rendering.

(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------
    let allBeys = [];          // raw beys_data.json array
    let eloMap = {};           // bey name → ELO value (from leaderboard CSV)
    let winrateMap = {};       // bey name → winrate (%)
    let matchesMap = {};       // bey name → match count
    let profileArchetypeMap = {}; // normalized blade → RPG/profile archetype object
    let network = null;        // vis.Network instance
    let nodesDataSet = null;
    let edgesDataSet = null;
    let currentFilter = 'all'; // 'all' | 'family' | 'suffix' | 'ratchet' | 'bit' | 'archetype'
    let selectedNodeId = null;

    // Edge colours per relationship type
    const EDGE_COLORS = {
        family:  { color: '#8b5cf6', highlight: '#a78bfa' },
        suffix:  { color: '#ec4899', highlight: '#f472b6' },
        ratchet: { color: '#3b82f6', highlight: '#60a5fa' },
        bit:     { color: '#f59e0b', highlight: '#fbbf24' },
        archetype: { color: '#10b981', highlight: '#34d399' },
    };

    // Archetype colours for node backgrounds
    const TYPE_COLORS = {
        Attack:  { bg: '#ef4444', border: '#b91c1c', font: '#ffffff' },
        Defense: { bg: '#3b82f6', border: '#1d4ed8', font: '#ffffff' },
        Stamina: { bg: '#10b981', border: '#047857', font: '#ffffff' },
        Balance: { bg: '#f59e0b', border: '#b45309', font: '#000000' },
    };
    const DEFAULT_NODE_COLOR = { bg: '#6b7280', border: '#374151', font: '#ffffff' };

    // ELO range used to scale node sizes
    const NODE_SIZE_MIN = 18;
    const NODE_SIZE_MAX = 50;
    const ELO_DEFAULT   = 1000;

    // -----------------------------------------------------------------------
    // DOM helpers
    // -----------------------------------------------------------------------
    function el(id) { return document.getElementById(id); }

    // -----------------------------------------------------------------------
    // Data loading
    // -----------------------------------------------------------------------
    async function loadBeysData() {
        const res = await fetch(DATA_PATHS.BEYS_DATA_JSON);
        if (!res.ok) throw new Error(`Failed to load beys data (${res.status})`);
        return res.json();
    }

    /** Parse a minimal CSV leaderboard to populate eloMap / winrateMap. */
    async function loadLeaderboardData() {
        try {
            const res = await fetch(DATA_PATHS.ADVANCED_LEADERBOARD_CSV);
            if (!res.ok) return;
            const text = await res.text();
            const lines = text.trim().split('\n');
            if (lines.length < 2) return;
            const headers = lines[0].split(',').map(h => h.trim());
            const nameIdx    = headers.indexOf('Name');
            const eloIdx     = headers.indexOf('ELO');
            const wrIdx      = headers.findIndex(h => h === 'Winrate' || h === 'Winrate_Xtreme');
            const matchesIdx = headers.findIndex(h => h === 'Matches' || h === 'Spiele');

            for (let i = 1; i < lines.length; i++) {
                const cols = lines[i].split(',');
                if (nameIdx < 0 || !cols[nameIdx]) continue;
                const name = cols[nameIdx].trim();
                if (eloIdx >= 0 && cols[eloIdx])  eloMap[name]      = parseFloat(cols[eloIdx]);
                if (wrIdx >= 0 && cols[wrIdx])     winrateMap[name]  = parseFloat(cols[wrIdx]);
                if (matchesIdx >= 0 && cols[matchesIdx]) matchesMap[name] = parseInt(cols[matchesIdx], 10);
            }
        } catch (err) {
            if (err instanceof SyntaxError) {
                console.warn('Leaderboard data parse error (continuing with defaults):', err.message);
            }
            // Network / 404 errors are expected when running without generated data
        }
    }

    function normalizeBeyName(name) {
        if (!name) return '';
        return name.toLowerCase().replace(/[\s\-_]/g, '');
    }

    async function loadProfileArchetypes() {
        try {
            const res = await fetch(DATA_PATHS.RPG_STATS_JSON);
            if (!res.ok) return;
            const rpgStats = await res.json();
            profileArchetypeMap = {};
            for (const [key, value] of Object.entries(rpgStats)) {
                if (value && value.archetype) {
                    profileArchetypeMap[normalizeBeyName(key)] = value.archetype;
                }
            }
        } catch (err) {
            // Running locally without generated analytics files is valid.
            profileArchetypeMap = {};
        }
    }

    // -----------------------------------------------------------------------
    // Graph construction helpers
    // -----------------------------------------------------------------------

    /** Map ELO value to a node size in [NODE_SIZE_MIN, NODE_SIZE_MAX]. */
    function eloToSize(elo) {
        const eloValues = Object.values(eloMap);
        if (eloValues.length === 0) return (NODE_SIZE_MIN + NODE_SIZE_MAX) / 2;
        const minElo = Math.min(...eloValues);
        const maxElo = Math.max(...eloValues);
        if (maxElo === minElo) return (NODE_SIZE_MIN + NODE_SIZE_MAX) / 2;
        const t = (elo - minElo) / (maxElo - minElo);
        return NODE_SIZE_MIN + t * (NODE_SIZE_MAX - NODE_SIZE_MIN);
    }

    function buildNodeId(bey) {
        // Stable ID: lower-case name with spaces replaced by underscores
        return bey.name.toLowerCase().replace(/\s+/g, '_');
    }

    /** Extract the blade family name (first CamelCase word), e.g. "DranSword" → "Dran". */
    function bladeFamilyOf(bey) {
        if (!bey.blade) return null;
        const m = bey.blade.match(/^([A-Z][a-z]*)/);
        return m ? m[1] : null;
    }

    /** Extract the blade suffix name (last CamelCase word), e.g. "CerberusFlame" → "Flame". */
    function bladeSuffixOf(bey) {
        if (!bey.blade) return null;
        const words = bey.blade.match(/[A-Z][a-z]*/g);
        if (!words || words.length < 2) return null; // single-word blade has no meaningful suffix distinct from family
        return words[words.length - 1];
    }

    function profileArchetypeNameOf(bey) {
        if (!bey || !bey.blade) return null;
        const data = profileArchetypeMap[normalizeBeyName(bey.blade)];
        return data && data.name ? data.name : null;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function sanitizeImageSrc(value) {
        const src = String(value || '').trim();
        if (!src) return '';
        if (/^(https?:|\/|\.\/|\.\.\/)/i.test(src)) return src;
        return '';
    }

    function buildNodes(beys) {
        return beys.map(bey => {
            const id      = buildNodeId(bey);
            const rawElo  = eloMap[bey.name];
            const hasElo  = Number.isFinite(rawElo);
            const elo     = hasElo ? rawElo : ELO_DEFAULT;
            const size    = eloToSize(elo);
            const tc      = TYPE_COLORS[bey.type] || DEFAULT_NODE_COLOR;

            return {
                id,
                label: bey.name,
                title: bey.name,  // used by vis as tooltip – overridden below
                size,
                shape: 'dot',
                color: {
                    background: tc.bg,
                    border:     tc.border,
                    highlight:  { background: tc.bg, border: '#ffffff' },
                    hover:      { background: tc.bg, border: '#ffffff' },
                },
                font: {
                    color: tc.font,
                    size:  12,
                    face:  'Inter, sans-serif',
                },
                // store extra data for the info panel
                _bey: bey,
                _elo: elo,
                _hasElo: hasElo,
            };
        });
    }

    function buildEdges(beys, filterType) {
        const edges = [];
        let edgeId  = 0;

        const addEdge = (fromId, toId, type, label) => {
            if (filterType !== 'all' && type !== filterType) return;
            const col = EDGE_COLORS[type];
            edges.push({
                id:    edgeId++,
                from:  fromId,
                to:    toId,
                label,
                title: `${type}: ${label}`,
                color: { color: col.color, highlight: col.highlight, hover: col.highlight },
                width: 2,
                smooth: { type: 'dynamic' },
                _type: type,
            });
        };

        for (let i = 0; i < beys.length; i++) {
            for (let j = i + 1; j < beys.length; j++) {
                const a = beys[i];
                const b = beys[j];
                const ai = buildNodeId(a);
                const bi = buildNodeId(b);

                // Same blade family (e.g. Dran* → "Dran")
                const famA = bladeFamilyOf(a);
                const famB = bladeFamilyOf(b);
                if (famA && famA === famB) {
                    addEdge(ai, bi, 'family', famA);
                }
                // Same blade suffix, different family (e.g. CerberusFlame ↔ WhaleFlame → "Flame")
                const sufA = bladeSuffixOf(a);
                const sufB = bladeSuffixOf(b);
                if (sufA && sufA === sufB && famA !== famB) {
                    addEdge(ai, bi, 'suffix', sufA);
                }
                // Same ratchet
                if (a.ratchet && b.ratchet && a.ratchet === b.ratchet) {
                    addEdge(ai, bi, 'ratchet', a.ratchet);
                }
                // Same bit
                if (a.bit && b.bit && a.bit === b.bit) {
                    addEdge(ai, bi, 'bit', a.bit);
                }
            }
        }

        // Profile archetype links (sparse): chain nodes that share the same RPG archetype.
        // If RPG data is unavailable, fallback to the broad type field so the graph stays usable.
        const archetypeGroups = new Map();
        beys.forEach(bey => {
            const archetypeName = profileArchetypeNameOf(bey) || bey.type;
            if (!archetypeName) return;
            if (!archetypeGroups.has(archetypeName)) archetypeGroups.set(archetypeName, []);
            archetypeGroups.get(archetypeName).push(bey);
        });
        archetypeGroups.forEach((group, archetype) => {
            if (group.length < 2) return;
            const sortedGroup = group.slice().sort((a, b) => a.name.localeCompare(b.name));
            for (let i = 1; i < sortedGroup.length; i++) {
                addEdge(
                    buildNodeId(sortedGroup[i - 1]),
                    buildNodeId(sortedGroup[i]),
                    'archetype',
                    archetype
                );
            }
        });

        return edges;
    }

    // -----------------------------------------------------------------------
    // vis-network initialisation / refresh
    // -----------------------------------------------------------------------

    function getNetworkOptions(isDark) {
        return {
            nodes: {
                borderWidth: 2,
                shadow: true,
            },
            edges: {
                width: 2,
                shadow: false,
                font: {
                    size: 10,
                    align: 'middle',
                    color: isDark ? '#e5e7eb' : '#1f2937',
                    strokeWidth: 2,
                    strokeColor: isDark ? 'rgba(17,24,39,0.9)' : 'rgba(255,255,255,0.9)',
                },
                arrows: { to: false },
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 140,
                    springConstant: 0.04,
                    damping: 0.09,
                },
                stabilization: { iterations: 200, fit: true },
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true,
            },
            layout: {
                improvedLayout: true,
            },
        };
    }

    function initOrRefreshNetwork(isDark) {
        const container = el('network-canvas');
        if (!container) return;

        const nodes = buildNodes(allBeys);
        const edges = buildEdges(allBeys, currentFilter);

        nodesDataSet = new vis.DataSet(nodes);
        edgesDataSet = new vis.DataSet(edges);

        if (network) {
            network.destroy();
            network = null;
        }

        network = new vis.Network(
            container,
            { nodes: nodesDataSet, edges: edgesDataSet },
            getNetworkOptions(isDark)
        );

        network.on('click', onNodeClick);
        network.on('hoverNode', onNodeHover);
        network.on('blurNode', onNodeBlur);
        network.on('stabilizationIterationsDone', () => {
            network.setOptions({ physics: { enabled: false } });
        });

        updateEdgeCounts();
    }

    // -----------------------------------------------------------------------
    // Interaction handlers
    // -----------------------------------------------------------------------

    function onNodeClick(params) {
        if (params.nodes.length === 0) {
            // Clicked on canvas – deselect
            if (selectedNodeId !== null) {
                dimEdges();
                selectedNodeId = null;
                clearInfoPanel();
            }
            return;
        }
        selectedNodeId = params.nodes[0];
        showInfoPanel(selectedNodeId);
        highlightConnected(selectedNodeId);
    }

    function onNodeHover(params) {
        el('network-canvas').style.cursor = 'pointer';
    }

    function onNodeBlur() {
        el('network-canvas').style.cursor = 'default';
    }

    /** Highlight edges connected to nodeId and dim the rest. */
    function highlightConnected(nodeId) {
        if (!edgesDataSet) return;
        const updates = edgesDataSet.get().map(edge => {
            const connected = edge.from === nodeId || edge.to === nodeId;
            const type = edge._type;
            const col  = EDGE_COLORS[type] || EDGE_COLORS.ratchet;
            return {
                id:    edge.id,
                color: connected
                    ? { color: col.highlight, highlight: col.highlight, hover: col.highlight }
                    : { color: 'rgba(200,200,200,0.15)', highlight: 'rgba(200,200,200,0.3)' },
                width: connected ? 3 : 1,
            };
        });
        edgesDataSet.update(updates);
    }

    function dimEdges() {
        if (!edgesDataSet) return;
        const updates = edgesDataSet.get().map(edge => {
            const type = edge._type;
            const col  = EDGE_COLORS[type] || EDGE_COLORS.ratchet;
            return {
                id:    edge.id,
                color: { color: col.color, highlight: col.highlight, hover: col.highlight },
                width: 2,
            };
        });
        edgesDataSet.update(updates);
    }

    // -----------------------------------------------------------------------
    // Info panel
    // -----------------------------------------------------------------------

    function showInfoPanel(nodeId) {
        const node = nodesDataSet.get(nodeId);
        if (!node) return;
        const bey   = node._bey;
        const elo   = node._elo;
        const hasElo = node._hasElo;
        const wr    = winrateMap[bey.name];
        const games = matchesMap[bey.name];
        const panel = el('info-panel');
        const tc    = TYPE_COLORS[bey.type] || DEFAULT_NODE_COLOR;
        const safeName = escapeHtml(bey.name || '–');
        const safeType = escapeHtml(bey.type || '–');
        const safeBlade = escapeHtml(bey.blade || '–');
        const safeFamily = escapeHtml(bladeFamilyOf(bey) || '');
        const safeAssistBlade = escapeHtml(bey.assist_blade || '');
        const safeRatchet = escapeHtml(bey.ratchet || '–');
        const safeBit = escapeHtml(bey.bit || '–');
        const safeCode = escapeHtml(bey.code || '–');
        const safeDescription = escapeHtml(bey.description || '');
        const safeImage = sanitizeImageSrc(bey.image);
        const safeBeyLink = `bey.html?bey=${encodeURIComponent(String(bey.name || ''))}`;

        // Build connected neighbours info
        const connectedEdges = edgesDataSet.get({
            filter: e => e.from === nodeId || e.to === nodeId,
        });
        const relSummary = {};
        connectedEdges.forEach(e => {
            relSummary[e._type] = (relSummary[e._type] || 0) + 1;
        });
        const relLines = Object.entries(relSummary)
            .map(([t, c]) => `<span class="info-rel info-rel-${escapeHtml(t)}">${c} ${escapeHtml(t)}</span>`)
            .join('');

        panel.innerHTML = `
            <div class="info-panel-inner">
                <div class="info-header" style="background:${tc.bg};">
                    <h3 class="info-title" style="color:${tc.font}">${safeName}</h3>
                    <span class="info-type-badge" style="color:${tc.font}">${safeType}</span>
                </div>
                <div class="info-body">
                    ${safeImage ? `<img class="info-bey-img" src="${safeImage}" alt="${safeName}" loading="lazy">` : ''}
                    <div class="info-stats">
                        <div class="info-stat">
                            <span class="info-stat-label">ELO</span>
                            <span class="info-stat-value">${hasElo ? Math.round(elo) : '–'}</span>
                        </div>
                        <div class="info-stat">
                            <span class="info-stat-label">Win rate</span>
                            <span class="info-stat-value">${wr !== undefined ? wr.toFixed(1) + '%' : '–'}</span>
                        </div>
                        <div class="info-stat">
                            <span class="info-stat-label">Matches</span>
                            <span class="info-stat-value">${games !== undefined ? games : '–'}</span>
                        </div>
                    </div>
                    <table class="info-parts-table">
                        <tr><td class="ipt-label">Blade</td><td>${safeBlade}</td></tr>
                        ${safeFamily ? `<tr><td class="ipt-label">Family</td><td>${safeFamily}</td></tr>` : ''}
                        ${safeAssistBlade ? `<tr><td class="ipt-label">Assist</td><td>${safeAssistBlade}</td></tr>` : ''}
                        <tr><td class="ipt-label">Ratchet</td><td>${safeRatchet}</td></tr>
                        <tr><td class="ipt-label">Bit</td><td>${safeBit}</td></tr>
                        <tr><td class="ipt-label">Code</td><td>${safeCode}</td></tr>
                    </table>
                    ${safeDescription ? `<p class="info-desc">${safeDescription}</p>` : ''}
                    ${relLines ? `<div class="info-rels">${relLines}</div>` : ''}
                    <a class="info-wiki-link" href="${safeBeyLink}">View full stats →</a>
                </div>
            </div>
        `;
        panel.classList.add('visible');
    }

    function clearInfoPanel() {
        const panel = el('info-panel');
        panel.innerHTML = '<p class="info-placeholder">Click a node to see details</p>';
        panel.classList.remove('visible');
    }

    // -----------------------------------------------------------------------
    // Filter / control handlers
    // -----------------------------------------------------------------------

    function updateEdgeCounts() {
        if (!edgesDataSet) return;
        const edges = edgesDataSet.get();
        const counts = { family: 0, suffix: 0, ratchet: 0, bit: 0, archetype: 0 };
        edges.forEach(e => { if (counts[e._type] !== undefined) counts[e._type]++; });

        // Button badges
        const fEl = el('edge-count-family');
        const sEl = el('edge-count-suffix');
        const rEl = el('edge-count-ratchet');
        const bEl = el('edge-count-bit');
        const tEl = el('edge-count-archetype');
        if (fEl) fEl.textContent = counts.family;
        if (sEl) sEl.textContent = counts.suffix;
        if (rEl) rEl.textContent = counts.ratchet;
        if (bEl) bEl.textContent = counts.bit;
        if (tEl) tEl.textContent = counts.archetype;

        // Stats bar
        const fBar = el('edge-count-family-bar');
        const sBar = el('edge-count-suffix-bar');
        const rBar = el('edge-count-ratchet-bar');
        const bBar = el('edge-count-bit-bar');
        const tBar = el('edge-count-archetype-bar');
        if (fBar) fBar.textContent = counts.family;
        if (sBar) sBar.textContent = counts.suffix;
        if (rBar) rBar.textContent = counts.ratchet;
        if (bBar) bBar.textContent = counts.bit;
        if (tBar) tBar.textContent = counts.archetype;
    }

    function applyFilter(filter) {
        currentFilter = filter;
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });

        // Rebuild edges only (nodes stay the same)
        const edges = buildEdges(allBeys, filter);
        edgesDataSet.clear();
        edgesDataSet.add(edges);
        updateEdgeCounts();
        // Reset any highlight
        selectedNodeId = null;
        clearInfoPanel();
    }

    function searchNode(query) {
        if (!nodesDataSet || !network) return;
        const q = query.trim().toLowerCase();
        if (!q) {
            // Reset all node sizes / opacity
            nodesDataSet.update(nodesDataSet.get().map(n => ({
                id: n.id,
                opacity: 1,
            })));
            return;
        }
        const updates = nodesDataSet.get().map(n => {
            const match = n.label.toLowerCase().includes(q);
            return { id: n.id, opacity: match ? 1 : 0.15 };
        });
        nodesDataSet.update(updates);

        // Focus on first exact match if found
        const exact = nodesDataSet.get().find(n => n.label.toLowerCase().includes(q));
        if (exact) {
            network.focus(exact.id, { scale: 1.4, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
            showInfoPanel(exact.id);
        }
    }

    // -----------------------------------------------------------------------
    // Legend
    // -----------------------------------------------------------------------

    function buildLegend() {
        const legendEl = el('legend');
        if (!legendEl) return;
        legendEl.innerHTML = `
            <h4>Node class type</h4>
            ${Object.entries(TYPE_COLORS).map(([t, c]) =>
                `<div class="legend-item"><span class="legend-dot" style="background:${c.bg};border-color:${c.border}"></span>${t}</div>`
            ).join('')}
            <h4 style="margin-top:12px">Edge relationship</h4>
            ${Object.entries(EDGE_COLORS).map(([t, c]) =>
                `<div class="legend-item"><span class="legend-line" style="background:${c.color}"></span>${t === 'archetype' ? 'Profile archetype' : t.charAt(0).toUpperCase() + t.slice(1)}</div>`
            ).join('')}
            <h4 style="margin-top:12px">Node size</h4>
            <div class="legend-item legend-size-hint">Larger = higher ELO</div>
        `;
    }

    // -----------------------------------------------------------------------
    // Bootstrapping
    // -----------------------------------------------------------------------

    async function init() {
        el('loading-message').textContent = 'Loading bey data…';

        try {
            [allBeys] = await Promise.all([
                loadBeysData(),
                loadLeaderboardData(),
                loadProfileArchetypes(),
            ]);
        } catch (err) {
            el('loading-message').textContent = 'Error loading data: ' + err.message;
            return;
        }

        el('loading-message').style.display = 'none';
        const wrapper = el('graph-wrapper');
        wrapper.style.display   = 'flex';
        // Set explicit pixel height so vis-network can render at the correct size
        const targetH = Math.max(480, window.innerHeight - 280);
        wrapper.style.height = targetH + 'px';

        const isDark = document.body.classList.contains('dark');
        initOrRefreshNetwork(isDark);
        buildLegend();
        clearInfoPanel();

        // Update node count badge
        const countEl = el('node-count');
        if (countEl) countEl.textContent = allBeys.length;

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => applyFilter(btn.dataset.filter));
        });

        // Search
        const searchInput = el('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', () => searchNode(searchInput.value));
        }

        // Reset button
        const resetBtn = el('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                nodesDataSet.update(nodesDataSet.get().map(n => ({ id: n.id, opacity: 1 })));
                dimEdges();
                selectedNodeId = null;
                clearInfoPanel();
                network.fit({ animation: { duration: 600 } });
            });
        }

        // Fit button
        const fitBtn = el('fit-btn');
        if (fitBtn) {
            fitBtn.addEventListener('click', () => {
                network.fit({ animation: { duration: 600 } });
            });
        }

        // Dark-mode toggle – re-init so the canvas background updates
        const darkToggle = el('darkToggle');
        if (darkToggle) {
            darkToggle.addEventListener('change', (event) => {
                const dark = Boolean(event.target && event.target.checked);
                initOrRefreshNetwork(dark);
                buildLegend();
            });
        }

        // Keep wrapper height in sync with window size
        window.addEventListener('resize', () => {
            const w = el('graph-wrapper');
            if (w && w.style.display !== 'none') {
                w.style.height = Math.max(480, window.innerHeight - 280) + 'px';
                if (network) network.redraw();
            }
        });

        // Stabilise physics after a few seconds to improve performance
        setTimeout(() => {
            if (network) network.setOptions({ physics: { enabled: false } });
        }, 4000);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
