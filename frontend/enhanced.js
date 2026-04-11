// SportsAI Enhanced JavaScript - Three-Layer Architecture Integration
// Olympic-grade volleyball analysis frontend functionality

class SportsAIEnhanced {
  constructor() {
    this.apiBaseUrl = 'http://localhost:8000';
    this.currentAnalysis = null;
    this.activeJobId = null;
    this.pollInterval = null;
    
    // Three-layer architecture state
    this.layerStates = {
      tactical: { status: 'idle', data: null },
      biomechanical: { status: 'idle', data: null },
      llm: { status: 'idle', data: null }
    };
    
    // Competition readiness state
    this.readinessState = {
      overall: 0,
      tactical: 0,
      biomechanical: 0,
      consistency: 0
    };
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupDragAndDrop();
    this.setupFileUploads();
    this.initializeCharts();
    this.checkAPIHealth();
  }

  // API Integration
  async checkAPIHealth() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/health`);
      const data = await response.json();
      this.updateConnectionStatus(data.status === 'healthy');
    } catch (error) {
      console.error('API Health Check Failed:', error);
      this.updateConnectionStatus(false);
    }
  }

  async submitComprehensiveAnalysis(formData) {
    try {
      this.showLoading('Submitting comprehensive analysis...');
      
      const response = await fetch(`${this.apiBaseUrl}/analyse/comprehensive`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Analysis submission failed');
      
      const data = await response.json();
      this.handleAnalysisResult(data);
      
    } catch (error) {
      this.showError('Analysis submission failed: ' + error.message);
    } finally {
      this.hideLoading();
    }
  }

  async submitPostMatchAnalysis(formData) {
    try {
      this.showLoading('Submitting post-match analysis...');
      
      const response = await fetch(`${this.apiBaseUrl}/analyse/post-match`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Post-match submission failed');
      
      const data = await response.json();
      this.activeJobId = data.job_id;
      this.startJobPolling();
      
      this.showSuccess(`Post-match analysis submitted! Job ID: ${data.job_id}`);
      this.updateJobStatus(data);
      
    } catch (error) {
      this.showError('Post-match submission failed: ' + error.message);
    } finally {
      this.hideLoading();
    }
  }

  async checkJobStatus(jobId) {
    try {
      const response = await fetch(`${this.apiBaseUrl}/analyse/post-match/status/${jobId}`);
      const data = await response.json();
      
      this.updateJobStatus(data);
      
      if (data.status === 'completed') {
        this.stopJobPolling();
        this.loadJobResults(jobId);
      } else if (data.status === 'failed') {
        this.stopJobPolling();
        this.showError('Analysis failed: ' + (data.error_message || 'Unknown error'));
      }
      
    } catch (error) {
      console.error('Job status check failed:', error);
    }
  }

  async loadJobResults(jobId) {
    try {
      const response = await fetch(`${this.apiBaseUrl}/analyse/post-match/report/${jobId}`);
      const data = await response.json();
      
      this.displayPostMatchResults(data);
      
    } catch (error) {
      this.showError('Failed to load results: ' + error.message);
    }
  }

  // Three-Layer Architecture Visualization
  updateLayerVisualization(layer, status, data = null) {
    const layerElement = document.querySelector(`[data-layer="${layer}"]`);
    if (!layerElement) return;

    // Update layer status
    layerElement.classList.remove('processing', 'completed', 'error');
    layerElement.classList.add(status);

    // Update progress indicator
    const progressElement = layerElement.querySelector('.layer-progress');
    if (progressElement) {
      const progress = this.calculateLayerProgress(layer, status);
      progressElement.style.width = `${progress}%`;
      progressElement.setAttribute('data-progress', progress);
    }

    // Update data display
    if (data) {
      this.displayLayerData(layer, data);
    }

    // Update overall progress
    this.updateOverallProgress();
  }

  calculateLayerProgress(layer, status) {
    const progressMap = {
      idle: 0,
      processing: 50,
      completed: 100,
      error: 0
    };
    return progressMap[status] || 0;
  }

  displayLayerData(layer, data) {
    const dataContainer = document.querySelector(`[data-layer-data="${layer}"]`);
    if (!dataContainer) return;

    switch (layer) {
      case 'tactical':
        this.displayTacticalData(data, dataContainer);
        break;
      case 'biomechanical':
        this.displayBiomechanicalData(data, dataContainer);
        break;
      case 'llm':
        this.displayLLMData(data, dataContainer);
        break;
    }
  }

  displayTacticalData(data, container) {
    const html = `
      <div class="tactical-summary">
        <div class="tactical-metric">
          <span class="metric-label">Total Actions</span>
          <span class="metric-value">${data.total_actions || 0}</span>
        </div>
        <div class="tactical-metric">
          <span class="metric-label">Rally Count</span>
          <span class="metric-value">${data.rally_count || 0}</span>
        </div>
        <div class="tactical-metric">
          <span class="metric-label">Serve Effectiveness</span>
          <span class="metric-value">${((data.serve_effectiveness?.effectiveness_score || 0) * 100).toFixed(0)}%</span>
        </div>
      </div>
      ${data.tactical_insights ? `
        <div class="tactical-insights">
          <h4>Key Insights</h4>
          ${data.tactical_insights.map(insight => `<div class="insight-item">${insight}</div>`).join('')}
        </div>
      ` : ''}
    `;
    container.innerHTML = html;
  }

  displayBiomechanicalData(data, container) {
    const html = `
      <div class="biomech-summary">
        <div class="biomech-metric">
          <span class="metric-label">Actions Analyzed</span>
          <span class="metric-value">${data.actions_analyzed || 0}</span>
        </div>
        <div class="biomech-metric">
          <span class="metric-label">Elite Alignment</span>
          <span class="metric-value">${((data.biomechanical_summary?.elite_alignment_percentage || 0)).toFixed(0)}%</span>
        </div>
        <div class="biomech-metric">
          <span class="metric-label">Consistency Score</span>
          <span class="metric-value">${((data.biomechanical_summary?.consistency_metrics?.consistency_score || 0) * 100).toFixed(0)}%</span>
        </div>
      </div>
      ${data.biomechanical_summary?.key_deviations ? `
        <div class="deviation-summary">
          <h4>Key Deviations</h4>
          ${data.biomechanical_summary.key_deviations.map(deviation => 
            `<div class="deviation-item">${deviation}</div>`
          ).join('')}
        </div>
      ` : ''}
    `;
    container.innerHTML = html;
  }

  displayLLMData(data, container) {
    const html = `
      <div class="llm-summary">
        <div class="llm-metric">
          <span class="metric-label">Training Recommendations</span>
          <span class="metric-value">${data.training_recommendations?.length || 0}</span>
        </div>
        <div class="llm-metric">
          <span class="metric-label">Competition Readiness</span>
          <span class="metric-value">${data.competition_readiness?.readiness_level || 'Unknown'}</span>
        </div>
      </div>
      ${data.training_recommendations ? `
        <div class="recommendations-summary">
          <h4>Training Focus</h4>
          ${data.training_recommendations.slice(0, 3).map(rec => 
            `<div class="recommendation-item">
              <span class="rec-category">${rec.category}</span>
              <span class="rec-description">${rec.description}</span>
            </div>`
          ).join('')}
        </div>
      ` : ''}
    `;
    container.innerHTML = html;
  }

  // Competition Readiness Dashboard
  updateReadinessDashboard(readinessData) {
    if (!readinessData) return;

    this.readinessState = {
      overall: readinessData.overall_readiness || 0,
      tactical: readinessData.tactical_readiness || 0,
      biomechanical: readinessData.biomechanical_readiness || 0,
      consistency: readinessData.consistency_score || 0
    };

    // Update readiness level display
    const levelElement = document.querySelector('.readiness-level-display');
    if (levelElement) {
      levelElement.textContent = readinessData.readiness_level || 'Unknown';
      levelElement.className = `readiness-level-display readiness-${readinessData.readiness_level}`;
    }

    // Update progress rings
    this.updateReadinessRing('overall', this.readinessState.overall);
    this.updateReadinessRing('tactical', this.readinessState.tactical);
    this.updateReadinessRing('biomechanical', this.readinessState.biomechanical);
    this.updateReadinessRing('consistency', this.readinessState.consistency);

    // Update recommendations
    this.displayReadinessRecommendations(readinessData.recommendations);
  }

  updateReadinessRing(type, value) {
    const ring = document.querySelector(`[data-readiness-ring="${type}"]`);
    if (!ring) return;

    const circle = ring.querySelector('circle:last-child');
    const text = ring.querySelector('.progress-text');
    
    if (circle) {
      const radius = circle.r.baseVal.value;
      const circumference = 2 * Math.PI * radius;
      const offset = circumference - (value * circumference);
      
      circle.style.strokeDasharray = circumference;
      circle.style.strokeDashoffset = offset;
      circle.style.stroke = this.getReadinessColor(value);
    }
    
    if (text) {
      text.textContent = `${Math.round(value * 100)}%`;
    }
  }

  getReadinessColor(value) {
    if (value >= 0.85) return 'var(--ready-elite)';
    if (value >= 0.70) return 'var(--ready-near)';
    if (value >= 0.55) return 'var(--ready-dev)';
    return 'var(--ready-work)';
  }

  displayReadinessRecommendations(recommendations) {
    const container = document.querySelector('.readiness-recommendations');
    if (!container || !recommendations) return;

    const html = recommendations.map((rec, index) => `
      <div class="recommendation-card">
        <div class="rec-number">${index + 1}</div>
        <div class="rec-content">
          <div class="rec-text">${rec}</div>
        </div>
      </div>
    `).join('');

    container.innerHTML = html;
  }

  // Court Visualization
  updateCourtVisualization(trackingData) {
    if (!trackingData) return;

    const court = document.querySelector('.court-diagram');
    if (!court) return;

    // Clear existing markers
    const existingMarkers = court.querySelectorAll('.player-marker');
    existingMarkers.forEach(marker => marker.remove());

    // Add player markers
    if (trackingData.players_tracked) {
      this.addPlayerMarkers(court, trackingData);
    }

    // Update tracking statistics
    this.updateTrackingStats(trackingData);
  }

  addPlayerMarkers(court, data) {
    const positions = this.calculatePlayerPositions(data);
    
    positions.forEach((player, index) => {
      const marker = document.createElement('div');
      marker.className = `player-marker ${player.status}`;
      marker.style.left = `${player.x}%`;
      marker.style.top = `${player.y}%`;
      marker.textContent = player.number || '?';
      marker.title = `${player.position} - ${player.status}`;
      
      marker.addEventListener('click', () => {
        this.showPlayerDetails(player);
      });
      
      court.appendChild(marker);
    });
  }

  calculatePlayerPositions(data) {
    // Simulate player positions based on tracking data
    // In real implementation, this would use actual coordinates
    const positions = [];
    const courtWidth = 90; // Percentage of court width
    const courtHeight = 80; // Percentage of court height
    
    for (let i = 0; i < Math.min(data.players_tracked, 12); i++) {
      positions.push({
        x: 5 + (i % 6) * (courtWidth / 6),
        y: 10 + Math.floor(i / 6) * (courtHeight / 2),
        number: data.jersey_recognition?.jersey_numbers[i] || '?',
        position: this.getPlayerPosition(i),
        status: i < data.jersey_recognition?.detected_jerseys ? 'tracked' : 'analyzed'
      });
    }
    
    return positions;
  }

  getPlayerPosition(index) {
    const positions = ['Outside', 'Setter', 'Middle', 'Opposite', 'Libero', 'Outside'];
    return positions[index % positions.length];
  }

  showPlayerDetails(player) {
    const modal = document.getElementById('playerDetailsModal');
    if (modal) {
      const content = modal.querySelector('.modal-body');
      content.innerHTML = `
        <div class="player-details">
          <h3>Player #${player.number}</h3>
          <p><strong>Position:</strong> ${player.position}</p>
          <p><strong>Status:</strong> ${player.status}</p>
          <p><strong>Tracking Quality:</strong> ${player.status === 'tracked' ? 'High' : 'Medium'}</p>
        </div>
      `;
      modal.classList.add('active');
    }
  }

  updateTrackingStats(data) {
    const statsContainer = document.querySelector('.tracking-stats');
    if (!statsContainer) return;

    const html = `
      <div class="stat-grid">
        <div class="stat-item">
          <div class="stat-value">${data.players_tracked || 0}</div>
          <div class="stat-label">Players Tracked</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${data.jersey_recognition?.detected_jerseys || 0}</div>
          <div class="stat-label">Jerseys Detected</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${Math.round((data.jersey_recognition?.recognition_accuracy || 0) * 100)}%</div>
          <div class="stat-label">Recognition Accuracy</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${Math.round((data.tracking_quality || 0) * 100)}%</div>
          <div class="stat-label">Tracking Quality</div>
        </div>
      </div>
    `;
    
    statsContainer.innerHTML = html;
  }

  // Action Timeline Visualization
  updateActionTimeline(actions) {
    if (!actions || !actions.length) return;

    const timeline = document.querySelector('.action-timeline');
    if (!timeline) return;

    const timelineBar = timeline.querySelector('.timeline-bar');
    const markers = timeline.querySelector('.timeline-markers');
    
    if (timelineBar) {
      timelineBar.style.width = '100%';
    }
    
    if (markers) {
      markers.innerHTML = '';
      
      // Add action markers
      actions.slice(0, 8).forEach((action, index) => {
        const marker = document.createElement('div');
        marker.className = 'timeline-marker';
        marker.style.left = `${(index / (actions.length - 1)) * 100}%`;
        marker.setAttribute('data-time', `${action.start_time.toFixed(1)}s`);
        marker.title = `${action.action_type} (${action.confidence.toFixed(2)})`;
        
        marker.addEventListener('click', () => {
          this.showActionDetails(action);
        });
        
        markers.appendChild(marker);
      });
    }
  }

  showActionDetails(action) {
    const modal = document.getElementById('actionDetailsModal');
    if (modal) {
      const content = modal.querySelector('.modal-body');
      content.innerHTML = `
        <div class="action-details">
          <h3>${action.action_type.toUpperCase()}</h3>
          <p><strong>Time:</strong> ${action.start_time.toFixed(1)}s - ${action.end_time.toFixed(1)}s</p>
          <p><strong>Confidence:</strong> ${(action.confidence * 100).toFixed(0)}%</p>
          <p><strong>Duration:</strong> ${(action.end_time - action.start_time).toFixed(1)}s</p>
          ${action.player_id ? `<p><strong>Player:</strong> #${action.player_id}</p>` : ''}
          ${action.zone ? `<p><strong>Zone:</strong> ${action.zone}</p>` : ''}
        </div>
      `;
      modal.classList.add('active');
    }
  }

  // FIVB Benchmark Visualization
  updateBenchmarkVisualization(benchmarks) {
    if (!benchmarks) return;

    const container = document.querySelector('.benchmark-visualization');
    if (!container) return;

    const html = Object.entries(benchmarks).map(([joint, data]) => {
      const assessment = data.assessment || 'unknown';
      const color = this.getBenchmarkColor(assessment);
      
      return `
        <div class="benchmark-item">
          <div class="benchmark-joint">${joint.replace('_', ' ').toUpperCase()}</div>
          <div class="benchmark-bar">
            <div class="benchmark-fill ${assessment}" style="width: ${this.getBenchmarkWidth(assessment)}%; background: ${color}"></div>
          </div>
          <div class="benchmark-assessment">${assessment.toUpperCase()}</div>
        </div>
      `;
    }).join('');
    
    container.innerHTML = html;
  }

  getBenchmarkColor(assessment) {
    const colors = {
      elite: 'var(--ready-elite)',
      good: 'var(--ready-near)',
      needs_improvement: 'var(--ready-dev)',
      significant_deviation: 'var(--ready-work)'
    };
    return colors[assessment] || 'var(--muted)';
  }

  getBenchmarkWidth(assessment) {
    const widths = {
      elite: 85,
      good: 70,
      needs_improvement: 50,
      significant_deviation: 30
    };
    return widths[assessment] || 50;
  }

  // UI Helpers
  showLoading(message = 'Processing...') {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
      const messageEl = loading.querySelector('.loading-message');
      if (messageEl) messageEl.textContent = message;
      loading.classList.add('active');
    }
  }

  hideLoading() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
      loading.classList.remove('active');
    }
  }

  showError(message) {
    this.showNotification(message, 'error');
  }

  showSuccess(message) {
    this.showNotification(message, 'success');
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-message">${message}</span>
        <button class="notification-close">&times;</button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      notification.remove();
    }, 5000);
    
    // Manual close
    notification.querySelector('.notification-close').addEventListener('click', () => {
      notification.remove();
    });
  }

  updateConnectionStatus(connected) {
    const statusElement = document.querySelector('.connection-status');
    if (statusElement) {
      statusElement.textContent = connected ? 'Connected' : 'Disconnected';
      statusElement.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
    }
  }

  // Event Listeners
  setupEventListeners() {
    // Modal controls
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-close')) {
        e.target.closest('.modal').classList.remove('active');
      }
      
      if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
      }
    });

    // Layer card interactions
    document.querySelectorAll('.layer-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn')) {
          this.toggleLayerDetails(card);
        }
      });
    });

    // Technique selection
    document.querySelectorAll('.tech-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        this.selectTechnique(e.target.dataset.tech);
      });
    });
  }

  setupDragAndDrop() {
    const uploadZones = document.querySelectorAll('.upload-zone-enhanced');
    
    uploadZones.forEach(zone => {
      zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
      });
      
      zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
      });
      
      zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          this.handleFileUpload(files[0], zone);
        }
      });
    });
  }

  setupFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
      input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          this.handleFileUpload(file, input.closest('.upload-zone-enhanced'));
        }
      });
    });
  }

  handleFileUpload(file, container) {
    const fileInfo = container.querySelector('.file-info');
    if (fileInfo) {
      fileInfo.innerHTML = `
        <div class="file-details">
          <div class="file-name">${file.name}</div>
          <div class="file-size">${this.formatFileSize(file.size)}</div>
        </div>
      `;
    }
    
    // Update UI state
    container.classList.add('file-uploaded');
    
    // Trigger analysis if auto-analyze is enabled
    if (container.dataset.autoAnalyze === 'true') {
      this.processUploadedFile(file, container);
    }
  }

  processUploadedFile(file, container) {
    const formData = new FormData();
    formData.append('video', file);
    
    // Add technique selection
    const activeTech = document.querySelector('.tech-pill.active');
    if (activeTech) {
      formData.append('technique', activeTech.dataset.tech);
    }
    
    // Add additional parameters based on upload type
    const uploadType = container.dataset.uploadType;
    
    if (uploadType === 'comprehensive') {
      this.submitComprehensiveAnalysis(formData);
    } else if (uploadType === 'post-match') {
      this.submitPostMatchAnalysis(formData);
    }
  }

  // Job Polling
  startJobPolling() {
    if (this.pollInterval) return;
    
    this.pollInterval = setInterval(() => {
      if (this.activeJobId) {
        this.checkJobStatus(this.activeJobId);
      }
    }, 30000); // Poll every 30 seconds
  }

  stopJobPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  updateJobStatus(data) {
    const statusElement = document.querySelector('.job-status-display');
    if (statusElement) {
      statusElement.textContent = data.status;
      statusElement.className = `job-status-display status-${data.status}`;
    }
    
    const progressElement = document.querySelector('.job-progress-bar');
    if (progressElement && data.processing_time) {
      const estimatedTotal = 6 * 60 * 60; // 6 hours in seconds
      const progress = Math.min((data.processing_time / estimatedTotal) * 100, 95);
      progressElement.style.width = `${progress}%`;
    }
  }

  // Chart Initialization
  initializeCharts() {
    // Initialize Chart.js or other visualization libraries
    // This would be expanded based on specific chart requirements
    
    // Example: Initialize readiness chart
    const readinessCanvas = document.getElementById('readinessChart');
    if (readinessCanvas && typeof Chart !== 'undefined') {
      this.readinessChart = new Chart(readinessCanvas, {
        type: 'radar',
        data: {
          labels: ['Tactical', 'Biomechanical', 'Consistency', 'Overall'],
          datasets: [{
            label: 'Readiness Score',
            data: [0, 0, 0, 0],
            borderColor: 'var(--red)',
            backgroundColor: 'rgba(232, 23, 44, 0.1)',
            pointBackgroundColor: 'var(--red)'
          }]
        },
        options: {
          responsive: true,
          scales: {
            r: {
              beginAtZero: true,
              max: 1
            }
          }
        }
      });
    }
  }

  updateReadinessChart() {
    if (this.readinessChart) {
      this.readinessChart.data.datasets[0].data = [
        this.readinessState.tactical,
        this.readinessState.biomechanical,
        this.readinessState.consistency,
        this.readinessState.overall
      ];
      this.readinessChart.update();
    }
  }

  // Utility Functions
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  selectTechnique(technique) {
    // Update active technique
    document.querySelectorAll('.tech-pill').forEach(pill => {
      pill.classList.remove('active');
    });
    
    const activePill = document.querySelector(`[data-tech="${technique}"]`);
    if (activePill) {
      activePill.classList.add('active');
    }
    
    // Update UI based on technique
    this.updateTechniqueSpecificUI(technique);
  }

  updateTechniqueSpecificUI(technique) {
    // Update benchmark displays
    const benchmarkContainer = document.querySelector('.technique-benchmarks');
    if (benchmarkContainer) {
      benchmarkContainer.setAttribute('data-technique', technique);
    }
    
    // Update form parameters
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      const techInput = form.querySelector('input[name="technique"]');
      if (techInput) {
        techInput.value = technique;
      }
    });
  }

  toggleLayerDetails(card) {
    const details = card.querySelector('.layer-details');
    if (details) {
      details.classList.toggle('expanded');
      
      // Update expand/collapse icon
      const icon = card.querySelector('.expand-icon');
      if (icon) {
        icon.textContent = details.classList.contains('expanded') ? '−' : '+';
      }
    }
  }

  updateOverallProgress() {
    const completedLayers = Object.values(this.layerStates).filter(state => state.status === 'completed').length;
    const totalLayers = Object.keys(this.layerStates).length;
    const overallProgress = (completedLayers / totalLayers) * 100;
    
    const progressBar = document.querySelector('.overall-progress-bar');
    if (progressBar) {
      progressBar.style.width = `${overallProgress}%`;
      progressBar.setAttribute('data-progress', Math.round(overallProgress));
    }
    
    const progressText = document.querySelector('.overall-progress-text');
    if (progressText) {
      progressText.textContent = `${Math.round(overallProgress)}% Complete`;
    }
  }

  displayPostMatchResults(data) {
    // Update three-layer states
    if (data.layer_1_tactical) {
      this.layerStates.tactical = { status: 'completed', data: data.layer_1_tactical };
      this.updateLayerVisualization('tactical', 'completed', data.layer_1_tactical);
    }
    
    if (data.layer_2_biomechanical) {
      this.layerStates.biomechanical = { status: 'completed', data: data.layer_2_biomechanical };
      this.updateLayerVisualization('biomechanical', 'completed', data.layer_2_biomechanical);
    }
    
    if (data.layer_3_llm_insights) {
      this.layerStates.llm = { status: 'completed', data: data.layer_3_llm_insights };
      this.updateLayerVisualization('llm', 'completed', data.layer_3_llm_insights);
    }
    
    // Update competition readiness
    if (data.competition_readiness) {
      this.updateReadinessDashboard(data.competition_readiness);
    }
    
    // Update action timeline
    if (data.biomechanical_analysis?.actions) {
      this.updateActionTimeline(data.biomechanical_analysis.actions);
    }
    
    // Update court visualization
    if (data.multi_player_tracking) {
      this.updateCourtVisualization(data.multi_player_tracking);
    }
    
    // Update benchmark visualization
    if (data.biomechanical_analysis?.elite_comparisons) {
      this.updateBenchmarkVisualization(data.biomechanical_analysis.elite_comparisons);
    }
    
    // Show results
    this.showResultsSection();
  }

  showResultsSection() {
    const resultsSection = document.querySelector('.results-section');
    if (resultsSection) {
      resultsSection.classList.remove('hidden');
      resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
  }

  handleAnalysisResult(data) {
    this.currentAnalysis = data;
    this.displayPostMatchResults(data);
  }

  // Modal Controls
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
    }
  }
}

// Initialize the enhanced system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.sportsAIEnhanced = new SportsAIEnhanced();
});