/**
 * Tournament Bracket Renderer
 * 
 * Renders interactive SVG brackets for Single Elimination and Double Elimination tournaments
 */

class BracketRenderer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.svg = null;
        this.width = 0;
        this.height = 0;
        this.roundWidth = 200;
        this.matchHeight = 80;
        this.matchSpacing = 20;
        this.padding = 40;
    }

    /**
     * Render a single elimination bracket
     */
    renderSingleElimination(matches, participants) {
        // Group matches by round
        const rounds = this.groupByRound(matches);
        const numRounds = rounds.length;
        
        // Calculate dimensions
        const maxMatchesInRound = Math.max(...rounds.map(r => r.length));
        this.width = (numRounds * this.roundWidth) + (this.padding * 2);
        this.height = (maxMatchesInRound * (this.matchHeight + this.matchSpacing)) + (this.padding * 2);
        
        // Create SVG
        this.createSVG();
        
        // Draw rounds
        rounds.forEach((roundMatches, roundIndex) => {
            this.drawRound(roundMatches, roundIndex, numRounds);
        });
        
        // Draw connectors
        this.drawConnectors(rounds);
    }

    /**
     * Render a double elimination bracket
     */
    renderDoubleElimination(matches, participants) {
        // Separate winners and losers brackets
        const winnersMatches = matches.filter(m => m.bracket === 'main');
        const losersMatches = matches.filter(m => m.bracket === 'losers');
        
        const winnersRounds = this.groupByRound(winnersMatches);
        const losersRounds = this.groupByRound(losersMatches);
        
        const numWinnersRounds = winnersRounds.length;
        const numLosersRounds = losersRounds.length;
        const maxRounds = Math.max(numWinnersRounds, numLosersRounds);
        
        // Calculate dimensions
        const maxWinnersMatches = winnersRounds.length > 0 ? Math.max(...winnersRounds.map(r => r.length)) : 0;
        const maxLosersMatches = losersRounds.length > 0 ? Math.max(...losersRounds.map(r => r.length)) : 0;
        
        this.width = (maxRounds * this.roundWidth) + (this.padding * 2);
        const winnersHeight = (maxWinnersMatches * (this.matchHeight + this.matchSpacing)) + this.padding;
        const losersHeight = (maxLosersMatches * (this.matchHeight + this.matchSpacing)) + this.padding;
        this.height = winnersHeight + losersHeight + (this.padding * 3);
        
        // Create SVG
        this.createSVG();
        
        // Draw winners bracket
        const winnersGroup = this.createGroup('winners-bracket');
        winnersGroup.setAttribute('transform', `translate(0, ${this.padding})`);
        winnersRounds.forEach((roundMatches, roundIndex) => {
            this.drawRound(roundMatches, roundIndex, numWinnersRounds, winnersGroup);
        });
        this.drawConnectors(winnersRounds, winnersGroup);
        
        // Draw losers bracket
        const losersGroup = this.createGroup('losers-bracket');
        losersGroup.setAttribute('transform', `translate(0, ${winnersHeight + this.padding * 2})`);
        losersRounds.forEach((roundMatches, roundIndex) => {
            this.drawRound(roundMatches, roundIndex, numLosersRounds, losersGroup, true);
        });
        this.drawConnectors(losersRounds, losersGroup, true);
        
        // Add bracket labels
        this.addBracketLabels(winnersGroup, losersGroup, winnersHeight);
    }

    createSVG() {
        this.container.innerHTML = '';
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', this.width);
        this.svg.setAttribute('height', this.height);
        this.svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
        this.svg.style.maxWidth = '100%';
        this.svg.style.height = 'auto';
        this.container.appendChild(this.svg);
        
        // Add styles
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        style.textContent = `
            .match-box { cursor: pointer; transition: all 0.3s ease; }
            .match-box:hover { filter: brightness(1.1); }
            .match-box.completed { opacity: 1; }
            .match-box.pending { opacity: 0.6; }
            .player-name { font-size: 14px; font-weight: 500; }
            .player-score { font-size: 16px; font-weight: 700; }
            .winner { fill: #4caf50; }
            .loser { fill: #666; }
            .connector { stroke: #999; stroke-width: 2; fill: none; }
            .bracket-label { font-size: 18px; font-weight: 700; fill: #333; }
        `;
        this.svg.appendChild(style);
    }

    createGroup(id) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('id', id);
        this.svg.appendChild(group);
        return group;
    }

    groupByRound(matches) {
        const rounds = {};
        matches.forEach(match => {
            if (!rounds[match.round]) {
                rounds[match.round] = [];
            }
            rounds[match.round].push(match);
        });
        return Object.keys(rounds).sort((a, b) => a - b).map(r => rounds[r]);
    }

    drawRound(matches, roundIndex, totalRounds, parentGroup = null, isLosersBracket = false) {
        const group = parentGroup || this.svg;
        const roundMatches = matches.sort((a, b) => a.match_num - b.match_num);
        
        roundMatches.forEach((match, matchIndex) => {
            const x = this.padding + (roundIndex * this.roundWidth);
            const roundHeight = roundMatches.length * (this.matchHeight + this.matchSpacing);
            const startY = (this.height - this.padding * 2 - roundHeight) / 2;
            const y = startY + (matchIndex * (this.matchHeight + this.matchSpacing));
            
            this.drawMatch(match, x, y, group, isLosersBracket);
        });
    }

    drawMatch(match, x, y, group, isLosersBracket = false) {
        const matchGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        matchGroup.setAttribute('class', `match-box ${match.status}`);
        matchGroup.setAttribute('data-match-id', match.match_id);
        
        // Background
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', this.roundWidth - 20);
        rect.setAttribute('height', this.matchHeight);
        rect.setAttribute('rx', 8);
        rect.setAttribute('fill', isLosersBracket ? '#fff5f5' : '#ffffff');
        rect.setAttribute('stroke', match.status === 'completed' ? '#4caf50' : '#ddd');
        rect.setAttribute('stroke-width', 2);
        matchGroup.appendChild(rect);
        
        // Player 1
        if (match.player_a) {
            const player1 = this.createPlayerRow(
                match.player_a,
                match.score_a || 0,
                x + 10,
                y + 20,
                match.winner === match.player_a
            );
            matchGroup.appendChild(player1);
        } else {
            this.createPlaceholder('TBD', x + 10, y + 20, matchGroup);
        }
        
        // Divider
        const divider = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        divider.setAttribute('x1', x + 10);
        divider.setAttribute('y1', y + this.matchHeight / 2);
        divider.setAttribute('x2', x + this.roundWidth - 30);
        divider.setAttribute('y2', y + this.matchHeight / 2);
        divider.setAttribute('stroke', '#eee');
        divider.setAttribute('stroke-width', 1);
        matchGroup.appendChild(divider);
        
        // Player 2
        if (match.player_b) {
            const player2 = this.createPlayerRow(
                match.player_b,
                match.score_b || 0,
                x + 10,
                y + this.matchHeight - 20,
                match.winner === match.player_b
            );
            matchGroup.appendChild(player2);
        } else {
            this.createPlaceholder('BYE', x + 10, y + this.matchHeight - 20, matchGroup);
        }
        
        // Add hover effect
        matchGroup.addEventListener('mouseenter', () => {
            this.highlightMatchPath(match.match_id);
        });
        
        matchGroup.addEventListener('mouseleave', () => {
            this.clearHighlights();
        });
        
        group.appendChild(matchGroup);
    }

    createPlayerRow(name, score, x, y, isWinner) {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        // Name
        const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        nameText.setAttribute('x', x);
        nameText.setAttribute('y', y);
        nameText.setAttribute('class', `player-name ${isWinner ? 'winner' : 'loser'}`);
        nameText.textContent = name.length > 20 ? name.substring(0, 17) + '...' : name;
        group.appendChild(nameText);
        
        // Score
        const scoreText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        scoreText.setAttribute('x', x + 140);
        scoreText.setAttribute('y', y);
        scoreText.setAttribute('class', `player-score ${isWinner ? 'winner' : 'loser'}`);
        scoreText.textContent = score;
        group.appendChild(scoreText);
        
        return group;
    }

    createPlaceholder(text, x, y, group) {
        const placeholder = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        placeholder.setAttribute('x', x);
        placeholder.setAttribute('y', y);
        placeholder.setAttribute('class', 'player-name');
        placeholder.setAttribute('fill', '#999');
        placeholder.textContent = text;
        group.appendChild(placeholder);
    }

    drawConnectors(rounds, group = null, isLosersBracket = false) {
        const parent = group || this.svg;
        
        for (let roundIndex = 0; roundIndex < rounds.length - 1; roundIndex++) {
            const currentRound = rounds[roundIndex];
            const nextRound = rounds[roundIndex + 1];
            
            for (let i = 0; i < nextRound.length; i++) {
                const match1Index = i * 2;
                const match2Index = i * 2 + 1;
                
                if (match1Index < currentRound.length) {
                    const x1 = this.padding + (roundIndex * this.roundWidth) + this.roundWidth - 20;
                    const x2 = this.padding + ((roundIndex + 1) * this.roundWidth);
                    
                    const roundHeight = currentRound.length * (this.matchHeight + this.matchSpacing);
                    const startY = (this.height - this.padding * 2 - roundHeight) / 2;
                    
                    const y1 = startY + (match1Index * (this.matchHeight + this.matchSpacing)) + this.matchHeight / 2;
                    const y2 = match2Index < currentRound.length ? 
                        startY + (match2Index * (this.matchHeight + this.matchSpacing)) + this.matchHeight / 2 : y1;
                    
                    const nextRoundHeight = nextRound.length * (this.matchHeight + this.matchSpacing);
                    const nextStartY = (this.height - this.padding * 2 - nextRoundHeight) / 2;
                    const yTarget = nextStartY + (i * (this.matchHeight + this.matchSpacing)) + this.matchHeight / 2;
                    
                    this.drawConnector(x1, y1, y2, x2, yTarget, parent);
                }
            }
        }
    }

    drawConnector(x1, y1, y2, x2, yTarget, group) {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        
        const d = `
            M ${x1} ${y1}
            L ${midX} ${y1}
            ${y1 !== y2 ? `L ${midX} ${y2}` : ''}
            L ${midX} ${midY}
            L ${midX} ${yTarget}
            L ${x2} ${yTarget}
        `;
        
        path.setAttribute('d', d);
        path.setAttribute('class', 'connector');
        group.appendChild(path);
    }

    addBracketLabels(winnersGroup, losersGroup, winnersHeight) {
        const winnersLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        winnersLabel.setAttribute('x', 20);
        winnersLabel.setAttribute('y', winnersHeight / 2);
        winnersLabel.setAttribute('class', 'bracket-label');
        winnersLabel.setAttribute('transform', `rotate(-90, 20, ${winnersHeight / 2})`);
        winnersLabel.textContent = 'WINNERS BRACKET';
        this.svg.appendChild(winnersLabel);
        
        const losersLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        losersLabel.setAttribute('x', 20);
        losersLabel.setAttribute('y', winnersHeight + this.padding * 2 + (this.height - winnersHeight - this.padding * 3) / 2);
        losersLabel.setAttribute('class', 'bracket-label');
        losersLabel.setAttribute('transform', `rotate(-90, 20, ${winnersHeight + this.padding * 2 + (this.height - winnersHeight - this.padding * 3) / 2})`);
        losersLabel.textContent = 'LOSERS BRACKET';
        this.svg.appendChild(losersLabel);
    }

    highlightMatchPath(matchId) {
        // Future enhancement: highlight the path from this match to the finals
        const matchBox = this.svg.querySelector(`[data-match-id="${matchId}"]`);
        if (matchBox) {
            matchBox.style.filter = 'brightness(1.2) drop-shadow(0 0 8px rgba(76, 175, 80, 0.5))';
        }
    }

    clearHighlights() {
        const boxes = this.svg.querySelectorAll('.match-box');
        boxes.forEach(box => {
            box.style.filter = '';
        });
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BracketRenderer;
}
