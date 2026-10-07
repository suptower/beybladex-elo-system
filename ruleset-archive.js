/**
 * ruleset-archive.js
 *
 * Renders the per-season ruleset cards on the Ruleset Archive sub-page.
 * Pulls season data from seasons.json / season_data.json and merges it with
 * a static catalogue of ruleset descriptions defined in RULESET_CATALOGUE.
 *
 * The catalogued data is intentionally human-curated so we can capture the
 * "why" behind each change - something the raw JSON can't express.
 */

const RULESET_CATALOGUE = {
    S1: {
        version: 1,
        versionLabel: 'v1 (Legacy)',
        headline: '3-tier flat league - original format',
        summary:
            'Season 1 launched the league as a 3-tier round-robin with 10 beys per tier, ' +
            'no Tier IV, and a single relegation-playoff pair at each tier boundary. ',
        structure: { tiers: 3, beysPerTier: 10, totalBeys: 30, totalMatches: 135, matchdaysPerTier: 9 },
        league: { format: 'Single round-robin within each tier', matchesPerBey: 9, pointsWin: 3, pointsDominant: 4, pointsLoss: 0, dominantThreshold: 'Shutout with score >= 4 (e.g. 4-0, 5-0, 6-0)' },
        promotionRelegation: { qualificationPool: 'Bottom 4 of T3 (positions 7-10) drop to the qualification pool' },
        seasonCup: { held: true, slots: { 1: 4, 2: 3, 3: 1}, format: 'Double-elimination (winners/losers brackets + grand final)', note: '8 qualifiers total: 4 (T1) + 3 (T2) + 1 (T3).' },
        notes: [
            'Tier size of 10 beys meant 45 round-robin matches per tier - a heavy schedule that often ran late into the season.',
            'No relegation playoff at the bottom of T3: positions 7-10 dropped straight to the qualification pool.'
        ]
    },
    S2: {
        version: 2,
        versionLabel: 'v2 (Current)',
        headline: '4-tier pyramid with Qualification Pool',
        summary:
            'Season 2 introduced a major reformat: a fourth tier (Tier IV) for new and ' +
            'relegated beys, smaller tiers of 8 for tighter round-robins, tier-scaled ' +
            'promotion/relegation counts, and the inaugural Season Cup.',
        structure: { tiers: 4, beysPerTier: 8, totalBeys: 32, totalMatches: 112, matchdaysPerTier: 7 },
        league: { format: 'Single round-robin within each tier', matchesPerBey: 7, pointsWin: 3, pointsDominant: 4, pointsLoss: 0, dominantThreshold: 'Shutout with score >= 4 (e.g. 4-0, 5-0, 6-0) - unchanged from S1' },
        promotionRelegation: { qualificationPool: 'Bottom 4 of T4 (positions 5-8) drop to the qualification pool; the top 2 of T4 auto-promote to T3' },
        seasonCup: { held: true, slots: { 1: 4, 2: 2, 3: 1, 4: 1 }, format: 'Double-elimination (winners/losers brackets + grand final)', note: '8 qualifiers total: 4 (T1) + 2 (T2) + 1 (T3) + 1 (T4).' },
        notes: [
            'Tier IV acts as a dedicated "Challengers Tier" - its bottom 4 must re-qualify via the qualification tournament.',
            'Tier composition for the next season is derived from promotion/relegation results rather than a fresh ELO snapshot.'
        ]
    },
    S3: {
        version: 2,
        versionLabel: 'v2 (Current)',
        headline: 'Continuation of the v2 format',
        summary:
            'Season 3 continues the v2 format without structural changes. Tier composition ' +
            'was rebuilt from S2 promotion/relegation results, and the qualification pool ' +
            'still feeds Tier IV vacancies.',
        structure: { tiers: 4, beysPerTier: 8, totalBeys: 32, totalMatches: 112, matchdaysPerTier: 7 },
        league: { format: 'Single round-robin within each tier', matchesPerBey: 7, pointsWin: 3, pointsDominant: 4, pointsLoss: 0, dominantThreshold: 'Shutout with score >= 4 (e.g. 4-0, 5-0, 6-0) - unchanged' },
        promotionRelegation: { qualificationPool: 'Bottom 4 of T4 (positions 5-8) drop to the qualification pool; the top 2 of T4 auto-promote to T3' },
        seasonCup: { held: true, slots: { 1: 4, 2: 2, 3: 1, 4: 1 }, format: 'Double-elimination (winners/losers brackets + grand final)', note: '8 qualifiers total: 4 (T1) + 2 (T2) + 1 (T3) + 1 (T4).' },
        notes: [
            'No structural change vs. S2 - ruleset v2 is now the stable "default" in src/season/season_manager.py.',
            'Tiers were initialised with initialize_season_from_results() using S2 promotion/relegation data.'
        ]
    },
    S4: {
        version: 3,
        versionLabel: 'v3 (Proposed)',
        headline: 'Proposed addition of championship rounds',
        summary:
            'Season 4 is a proposed reformat that builds on the v2 structure with the addition ' +
            'of championship rounds depending on tier. The proposal is still being refined and has not been implemented yet. ' +
            'The general idea is that Tier I will play a full double round-robin (14 matches per bey) to determine the champion. ' +
            'Tier II will split into a championship group (top 4) and a relegation group (bottom 4) after a single round-robin in order to determine promotion/relegation slots in a more exciting manner. ' +
            'Tier III will feature a top five round robin after the regular single round-robin to determine the champion and promotion slots, while Tier IV will remain unchanged as a pure round-robin with no playoffs. ',
        structure: { tiers: 4, beysPerTier: 8, totalBeys: 32, totalMatches: 'TBD', matchdaysPerTier: 'TBD' },
        league: { format: 'Single round-robin within each tier with championship rounds depending on tier', matchesPerBey: '7-14', pointsWin: 3, pointsDominant: 4, pointsLoss: 0, dominantThreshold: 'Shutout with score >= 4 (e.g. 4-0, 5-0, 6-0) - unchanged' },
        promotionRelegation: { qualificationPool: 'TBD' },
        seasonCup: { held: true, slots: { 1: 4, 2: 2, 3: 1, 4: 1 }, format: 'Double-elimination (winners/losers brackets + grand final)', note: '8 qualifiers total: 4 (T1) + 2 (T2) + 1 (T3) + 1 (T4).' },
        notes: [
            'This proposed format is still being refined and has not been implemented yet.',
        ]
    }
};

const SEASONS_ORDER = ['S1', 'S2', 'S3', 'S4'];

const V2_TIER_RULES = {
    1: { autoPromotions: 0, autoRelegations: 1, playoff: 'T1 #7 plays T2 #2 (relegation playoff)' },
    2: { autoPromotions: 1, autoRelegations: 2, playoff: 'T2 #6 plays T3 #3' },
    3: { autoPromotions: 2, autoRelegations: 2, playoff: 'T3 #6 plays T4 #3' },
    4: { autoPromotions: 2, autoRelegations: 0, playoff: 'No lower tier - bottom 4 (5-8) drop to qualification pool' }
};

const V1_TIER_RULES = {
    1: { autoPromotions: 0, autoRelegations: 2, playoff: 'T1 #8 plays T2 #3' },
    2: { autoPromotions: 2, autoRelegations: 2, playoff: 'T2 #8 plays T3 #3' },
    3: { autoPromotions: 2, autoRelegations: 0, playoff: 'No lower tier - bottom 4 (7-10) drop to qualification pool' }
};

const V3_CHAMPIONSHIP_ROUNDS = {
    1: 'Full double round-robin (14 matches per bey)',
    2: 'Split into championship group (top 4) and relegation group (bottom 4) after a single round-robin',
    3: 'Top five round robin after the regular single round-robin to determine the champion and promotion slots',
    4: 'No championship round - pure round-robin with no playoffs'
};

/* --- Date helpers --- */

function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatSeasonDateRange(meta) {
    const start = formatDate(meta && meta.start_date);
    const end = formatDate(meta && meta.end_date);
    if (start && end) return start + ' - ' + end;
    if (start) return 'From ' + start;
    if (end) return 'Until ' + end;
    return 'Dates TBD';
}

/* --- Entry point --- */

document.addEventListener('DOMContentLoaded', () => {
    loadAndRender();
});

async function loadAndRender() {
    const container = document.getElementById('ruleset-seasons-container');
    const toc = document.getElementById('ruleset-toc-list');

    try {
        const [metaResp, dataResp] = await Promise.all([
            fetch(DATA_PATHS.SEASONS_JSON).then((r) => (r.ok ? r.json() : {})),
            fetch(DATA_PATHS.SEASON_DATA_JSON).then((r) => (r.ok ? r.json() : {}))
        ]);

        const seasons = (dataResp && dataResp.seasons) || {};
        const meta = metaResp || {};

        // Overlay authoritative status / dates from seasons.json
        for (const seasonId of Object.keys(seasons)) {
            const m = meta[seasonId];
            if (m) {
                seasons[seasonId].status = m.status;
                seasons[seasonId].start_date = m.start_date;
                if (m.end_date !== undefined) seasons[seasonId].end_date = m.end_date;
            }
        }

        const seasonIds = SEASONS_ORDER.filter((id) => seasons[id] || RULESET_CATALOGUE[id]);

        if (!seasonIds.length) {
            container.innerHTML =
                '<div class="ruleset-empty">No seasons found in the data files yet.</div>';
            return;
        }

        // Latest season with a known catalogue is the "current" ruleset
        const catalogued = seasonIds.filter((id) => RULESET_CATALOGUE[id]);
        const currentSeasonId = catalogued.length
            ? catalogued[catalogued.length - 1]
            : seasonIds[seasonIds.length - 1];

        renderToc(toc, seasonIds, seasons, currentSeasonId);
        container.innerHTML = seasonIds
            .map((sid) => renderSeasonCard(sid, seasons[sid], currentSeasonId === sid))
            .join('');
    } catch (err) {
        console.error('Failed to load ruleset data', err);
        container.innerHTML =
            '<div class="ruleset-empty">Failed to load ruleset data. Check the console for details.</div>';
    }
}

/* --- Table of contents --- */

function renderToc(tocEl, seasonIds, seasons, currentSeasonId) {
    if (!tocEl) return;
    tocEl.innerHTML = seasonIds
        .map((sid) => {
            const meta = seasons[sid] || {};
            const cat = RULESET_CATALOGUE[sid];
            const isCurrent = sid === currentSeasonId;
            const isLegacy = cat && cat.version === 1;
            const dateStr = formatSeasonDateRange(meta);
            const badges = isCurrent
                ? ' <span class="toc-badge">Current</span>'
                : isLegacy
                ? ' <span class="toc-badge legacy">Legacy</span>'
                : '';
            return (
                '<li>' +
                '<a href="#ruleset-' + sid.toLowerCase() + '">' +
                '<span>' + sid + badges + '</span>' +
                '<span class="toc-date">' + dateStr + '</span>' +
                '</a>' +
                '</li>'
            );
        })
        .join('');
}

/* --- Summary card helpers --- */

function summaryItem(label, value) {
    return (
        '<div class="ruleset-summary-item">' +
        '<div class="ruleset-summary-label">' + label + '</div>' +
        '<div class="ruleset-summary-value">' + value + '</div>' +
        '</div>'
    );
}

/* --- Per-season card --- */

function renderSeasonCard(seasonId, seasonData, isCurrent) {
    const cat = RULESET_CATALOGUE[seasonId];
    if (!cat) {
        return '<div class="ruleset-empty">No ruleset data available for ' + seasonId + '.</div>';
    }

    const versionClass = cat.version === 1 ? 'v1' : 'v2';
    const versionLabel = isCurrent ? cat.versionLabel + ' - Current' : cat.versionLabel;
    const headerBadgeClass = isCurrent ? 'current' : versionClass;

    const dateStr = formatSeasonDateRange(seasonData);
    const status = (seasonData && seasonData.status) || 'unknown';
    const metaExtras = [];
    if (status === 'upcoming') metaExtras.push('<em>Upcoming</em>');
    if (status === 'active' && !(seasonData && seasonData.end_date)) metaExtras.push('<em>Active</em>');
    const metaLine = metaExtras.length ? ' - ' + metaExtras.join(', ') : '';

    return (
        '<article class="ruleset-season-card' + (isCurrent ? ' is-current' : '') +
        '" id="ruleset-' + seasonId.toLowerCase() + '">' +
        '<div class="ruleset-season-header">' +
        '<div class="ruleset-season-title">' +
        '<h3>' + seasonId + '</h3>' +
        '<span class="ruleset-version-badge ' + headerBadgeClass + '">' + versionLabel + '</span>' +
        '</div>' +
        '<div class="ruleset-season-meta">' + dateStr + metaLine + '</div>' +
        '</div>' +

        '<div class="ruleset-season-body">' +
        '<div>' +
        '<h4>📋 ' + cat.headline + '</h4>' +
        '<p>' + cat.summary + '</p>' +
        '</div>' +

        '<div>' +
        '<h4>🏟️ League structure</h4>' +
        '<div class="ruleset-summary-grid">' +
        summaryItem('Tiers', cat.structure.tiers) +
        summaryItem('Beys per tier', cat.structure.beysPerTier) +
        summaryItem('Beys in league', cat.structure.totalBeys) +
        summaryItem('League matches', cat.structure.totalMatches) +
        summaryItem('Matchdays / tier', cat.structure.matchdaysPerTier) +
        '</div>' +
        '</div>' +

        '<div class="ruleset-subsection">' +
        '<h4>🎯 League matches</h4>' +
        '<ul>' +
        '<li>' + cat.league.format + '</li>' +
        '<li>Each bey plays <strong>' + cat.league.matchesPerBey + '</strong> matches</li>' +
        '<li>Win &rarr; <strong>' + cat.league.pointsWin + '</strong> pts &middot; Dominant win &rarr; <strong>' +
        cat.league.pointsDominant + '</strong> pts &middot; Loss &rarr; ' + cat.league.pointsLoss + ' pts</li>' +
        '<li>Dominant-win definition: <strong>' + cat.league.dominantThreshold + '</strong></li>' +
        '</ul>' +
        '</div>' +

        (cat.version === 3 ? '<div>' +
        '<h4>🔥 Championship Rounds</h4>' +
        renderChampionshipRounds(cat) +
        '</div>' : '') +

        '<div>' +
        '<h4>↕️ Promotion & relegation</h4>' +
        renderPromotionRelegation(cat) +
        '</div>' +

        '<div class="ruleset-subsection">' +
        '<h4>🏆 Season Cup</h4>' +
        renderSeasonCup(cat) +
        '</div>' +

        (cat.notes && cat.notes.length
            ? '<div class="ruleset-notes">' +
              '<strong>Notes:</strong>' +
              '<ul style="margin:0.4rem 0 0;padding-left:1.25rem;">' +
              cat.notes.map((n) => '<li>' + n + '</li>').join('') +
              '</ul>' +
              '</div>'
            : '') +
        '</div>' +
        '</article>'
    );
}

function renderChampionshipRounds(cat) {
    const rounds = V3_CHAMPIONSHIP_ROUNDS;
    const tierKeys = Object.keys(rounds)
        .map((n) => parseInt(n, 10))
        .sort((a, b) => a - b);

    const cards = tierKeys
        .map((tier) => {
            const r = rounds[tier];
            return (
                '<div class="ruleset-tier-card t' + tier + '">' +
                '<div class="ruleset-tier-name">Tier ' + tier + '</div>' +
                '<div class="ruleset-tier-rules">' + r + '</div>' +
                '</div>'
            );
        })
        .join('');

    return '<div class="ruleset-tier-grid">' + cards + '</div>';
}

/* --- Promotion / relegation per-tier card grid --- */

function renderPromotionRelegation(cat) {
    const rules = cat.version === 1 ? V1_TIER_RULES : V2_TIER_RULES;
    const tierKeys = Object.keys(rules)
        .map((n) => parseInt(n, 10))
        .sort((a, b) => a - b);

    const cards = tierKeys
        .map((tier) => {
            const r = rules[tier];
            const parts = [];
            if (r.autoPromotions > 0) {
                parts.push('<span class="auto-promo">\u2191' + r.autoPromotions + ' auto-promote</span>');
            }
            if (r.autoRelegations > 0) {
                parts.push('<span class="auto-rel">\u2193' + r.autoRelegations + ' auto-relegate</span>');
            }
            if (r.playoff) {
                parts.push('<span class="playoff">\u2694\ufe0f ' + r.playoff + '</span>');
            }
            return (
                '<div class="ruleset-tier-card t' + tier + '">' +
                '<div class="ruleset-tier-name">Tier ' + tier + '</div>' +
                '<div class="ruleset-tier-rules">' + parts.join('<br>') + '</div>' +
                '</div>'
            );
        })
        .join('');

    const qualNote = cat.promotionRelegation.qualificationPool
        ? '<div class="ruleset-notes" style="margin-top:0.6rem;">' +
          '<strong>Qualification pool:</strong> ' + cat.promotionRelegation.qualificationPool +
          '</div>'
        : '';

    return '<div class="ruleset-tier-grid">' + cards + '</div>' + qualNote;
}

/* --- Season Cup block --- */

function renderSeasonCup(cat) {
    if (!cat.seasonCup.held) {
        return '<p style="color:var(--text-light);margin:0;">' + cat.seasonCup.note + '</p>';
    }
    const slots = cat.seasonCup.slots || {};
    const slotKeys = Object.keys(slots).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
    const total = slotKeys.reduce((acc, k) => acc + (slots[k] || 0), 0);
    const slotCards = slotKeys
        .map((t) =>
            '<div class="ruleset-cup-slot">' +
            '<div class="ruleset-cup-tier">Tier ' + t + '</div>' +
            '<div class="ruleset-cup-count">' + slots[t] + ' slot' + (slots[t] === 1 ? '' : 's') + '</div>' +
            '</div>'
        )
        .join('');

    return (
        '<p style="color:var(--text-light);margin:0 0 0.6rem;">' +
        '<strong>Format:</strong> ' + cat.seasonCup.format + '<br>' +
        '<strong>Qualification:</strong> ' + cat.seasonCup.note +
        '</p>' +
        '<div class="ruleset-cup-quals">' + slotCards + '</div>' +
        '<p style="color:var(--text-light);font-size:0.85rem;margin:0.5rem 0 0;">' +
        '<strong>Total qualifiers:</strong> ' + total +
        '</p>'
    );
}
