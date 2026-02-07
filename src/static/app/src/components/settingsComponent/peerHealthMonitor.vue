<template>
  <div class="peerHealthMonitor">
    <!-- Header -->
    <div class="d-flex align-items-center mb-4">
      <h5 class="mb-0">
        <i class="bi bi-heart-pulse me-2"></i>
        <LocaleText t="Peer Health Monitor"></LocaleText>
      </h5>
      <span
        class="badge ms-2"
        :class="healthData.running ? 'bg-success' : 'bg-secondary'"
      >
        <LocaleText :t="healthData.running ? 'Running' : 'Stopped'"></LocaleText>
      </span>
      <div class="ms-auto">
        <button
          class="btn btn-sm me-2"
          :class="healthData.running ? 'btn-outline-danger' : 'btn-outline-success'"
          @click="toggleMonitor"
          :disabled="loading"
        >
          <i class="bi" :class="healthData.running ? 'bi-stop-fill' : 'bi-play-fill'"></i>
          <LocaleText :t="healthData.running ? 'Stop' : 'Start'"></LocaleText>
        </button>
        <button
          class="btn btn-sm btn-outline-primary"
          @click="forceCycle"
          :disabled="loading || !healthData.running"
        >
          <i class="bi bi-arrow-clockwise"></i>
          <LocaleText t="Force Check"></LocaleText>
        </button>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="row mb-4" v-if="healthData.stats">
      <div class="col-md-3">
        <div class="card bg-dark">
          <div class="card-body text-center">
            <h3 class="mb-0">{{ healthData.stats.total_pings || 0 }}</h3>
            <small class="text-muted"><LocaleText t="Total Pings"></LocaleText></small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-dark">
          <div class="card-body text-center">
            <h3 class="mb-0 text-success">{{ healthData.stats.successful_pings || 0 }}</h3>
            <small class="text-muted"><LocaleText t="Successful"></LocaleText></small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-dark">
          <div class="card-body text-center">
            <h3 class="mb-0 text-danger">{{ healthData.stats.failed_pings || 0 }}</h3>
            <small class="text-muted"><LocaleText t="Failed"></LocaleText></small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-dark">
          <div class="card-body text-center">
            <h3 class="mb-0 text-info">{{ healthData.stats.endpoint_updates || 0 }}</h3>
            <small class="text-muted"><LocaleText t="Endpoint Updates"></LocaleText></small>
          </div>
        </div>
      </div>
    </div>

    <!-- Interface Configuration -->
    <div class="card bg-dark mb-4">
      <div class="card-header">
        <i class="bi bi-gear me-2"></i>
        <LocaleText t="Interface Configuration"></LocaleText>
      </div>
      <div class="card-body">
        <div class="row" v-if="Object.keys(healthData.interfaces || {}).length > 0">
          <div
            class="col-md-6 mb-3"
            v-for="(config, iface) in healthData.interfaces"
            :key="iface"
          >
            <div class="card bg-secondary bg-opacity-25">
              <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                  <h6 class="mb-0">{{ iface }}</h6>
                  <div class="form-check form-switch ms-auto">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      :checked="config.enabled"
                      @change="toggleInterface(iface, $event.target.checked)"
                    >
                    <label class="form-check-label">
                      <LocaleText :t="config.enabled ? 'Enabled' : 'Disabled'"></LocaleText>
                    </label>
                  </div>
                </div>

                <div class="row g-2">
                  <div class="col-6">
                    <label class="form-label small"><LocaleText t="Ping Interval (sec)"></LocaleText></label>
                    <input
                      type="number"
                      class="form-control form-control-sm"
                      :value="config.ping_interval"
                      @change="updateInterfaceConfig(iface, 'ping_interval', $event.target.value)"
                      min="10" max="300"
                    >
                  </div>
                  <div class="col-6">
                    <label class="form-label small"><LocaleText t="Keepalive (sec)"></LocaleText></label>
                    <input
                      type="number"
                      class="form-control form-control-sm"
                      :value="config.keepalive_value"
                      @change="updateInterfaceConfig(iface, 'keepalive_value', $event.target.value)"
                      min="10" max="120"
                    >
                  </div>
                </div>

                <div class="form-check mt-2">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    :checked="config.set_keepalive"
                    @change="updateInterfaceConfig(iface, 'set_keepalive', $event.target.checked)"
                  >
                  <label class="form-check-label small">
                    <LocaleText t="Auto-set PersistentKeepalive on server"></LocaleText>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-muted text-center py-3">
          <LocaleText t="No interfaces configured. Start monitoring to detect interfaces."></LocaleText>
        </div>
      </div>
    </div>

    <!-- Peers Health Table -->
    <div class="card bg-dark">
      <div class="card-header d-flex align-items-center">
        <i class="bi bi-people me-2"></i>
        <LocaleText t="Peers Health Status"></LocaleText>
        <span class="badge bg-success ms-2">
          {{ activePeersCount }} active
        </span>
        <span 
          class="badge bg-secondary ms-2" 
          v-if="offlinePeersCount > 0"
          style="cursor: pointer;"
          @click="showOfflinePeers = !showOfflinePeers"
          :title="showOfflinePeers ? 'Click to hide offline peers' : 'Click to show offline peers'"
        >
          <i class="bi" :class="showOfflinePeers ? 'bi-eye-slash' : 'bi-eye'"></i>
          {{ offlinePeersCount }} offline
        </span>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-dark table-hover mb-0">
            <thead>
              <tr>
                <th><LocaleText t="Status"></LocaleText></th>
                <th><LocaleText t="Interface"></LocaleText></th>
                <th><LocaleText t="Name"></LocaleText></th>
                <th><LocaleText t="VPN IP"></LocaleText></th>
                <th><LocaleText t="Pingable"></LocaleText></th>
                <th>RTT</th>
                <th><LocaleText t="Success Rate"></LocaleText></th>
                <th><LocaleText t="Last Ping"></LocaleText></th>
                <th><LocaleText t="Endpoint"></LocaleText></th>
                <th><LocaleText t="Actions"></LocaleText></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(peer, pk) in sortedPeers" :key="pk">
                <td>
                  <span class="badge" :class="getStatusBadgeClass(peer.status)">
                    {{ getStatusLabel(peer.status) }}
                  </span>
                  <i
                    v-if="peer.endpoint_changed"
                    class="bi bi-arrow-repeat text-warning ms-1"
                    title="Endpoint recently changed"
                  ></i>
                </td>
                <td>
                  <code class="small">{{ peer.interface }}</code>
                </td>
                <td>
                  <span v-if="peer.name" class="text-info">{{ peer.name }}</span>
                  <span v-else class="text-muted small">{{ pk.substring(0, 8) }}...</span>
                </td>
                <td>
                  <code>{{ peer.vpn_ip }}</code>
                </td>
                <td>
                  <i
                    class="bi"
                    :class="getPingableIcon(peer)"
                  ></i>
                </td>
                <td>
                  <span v-if="peer.last_ping_success">
                    {{ peer.ping_rtt_ms }} ms
                  </span>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <div class="progress" style="height: 20px; width: 80px;" v-if="peer.status !== 'offline' && peer.status !== 'unknown'">
                    <div
                      class="progress-bar"
                      :class="getSuccessRateClass(peer.ping_success_rate)"
                      :style="{ width: peer.ping_success_rate + '%' }"
                    >
                      {{ peer.ping_success_rate }}%
                    </div>
                  </div>
                  <span v-else class="text-muted">-</span>
                </td>
                <td>
                  <small class="text-muted">
                    {{ formatTime(peer.last_ping_time) }}
                  </small>
                </td>
                <td>
                  <code class="small text-truncate d-inline-block" style="max-width: 150px;">
                    {{ peer.last_endpoint || '-' }}
                  </code>
                </td>
                <td>
                  <button
                    class="btn btn-sm btn-outline-primary"
                    @click="pingPeer(pk)"
                    :disabled="loading || peer.status === 'offline'"
                    title="Ping now"
                  >
                    <i class="bi bi-broadcast"></i>
                  </button>
                </td>
              </tr>
              <tr v-if="Object.keys(healthData.peers || {}).length === 0">
                <td colspan="10" class="text-center text-muted py-4">
                  <LocaleText :t="healthData.running ? 'Waiting for first check cycle...' : 'No peer health data available. Start monitoring to collect data.'"></LocaleText>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Status Legend -->
    <div class="mt-3 small text-muted">
      <span class="badge bg-success me-2">online</span> Connected, ping OK
      <span class="badge bg-info text-dark me-2 ms-3">unpingable</span> Connected, firewall blocks ping
      <span class="badge bg-warning text-dark me-2 ms-3">recent</span> Handshake 3-15 min ago
      <span v-if="showOfflinePeers" class="badge bg-danger me-2 ms-3">offline</span>
      <span v-if="showOfflinePeers"> Not connected (not pinged)</span>
    </div>

    <!-- Last Cycle Info -->
    <div class="text-muted small mt-3 text-end" v-if="healthData.stats?.last_cycle_time">
      <LocaleText t="Last check"></LocaleText>: {{ formatDateTime(healthData.stats.last_cycle_time) }}
      ({{ healthData.stats.last_cycle_duration_ms }} ms)
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { fetchGet, fetchPost } from '@/utilities/fetch'
import LocaleText from '@/components/text/localeText.vue'

const healthData = ref({
  running: false,
  peers: {},
  interfaces: {},
  stats: {}
})
const loading = ref(false)
const showOfflinePeers = ref(false)
let refreshInterval = null

// Filter and sort peers: hide offline/unknown by default, online first
const sortedPeers = computed(() => {
  const statusOrder = {
    'online': 0,
    'unpingable': 1,
    'recent': 2,
    'offline': 3,
    'unknown': 4
  }
  
  let entries = Object.entries(healthData.value.peers || {})
  
  // Filter out offline and unknown peers unless showOfflinePeers is true
  if (!showOfflinePeers.value) {
    entries = entries.filter(([_, peer]) => 
      peer.status !== 'offline' && peer.status !== 'unknown'
    )
  }
  
  entries.sort((a, b) => {
    const orderA = statusOrder[a[1].status] ?? 5
    const orderB = statusOrder[b[1].status] ?? 5
    return orderA - orderB
  })
  
  return Object.fromEntries(entries)
})

// Count of hidden offline peers
const offlinePeersCount = computed(() => {
  const entries = Object.entries(healthData.value.peers || {})
  return entries.filter(([_, peer]) => 
    peer.status === 'offline' || peer.status === 'unknown'
  ).length
})

// Count of active (shown) peers
const activePeersCount = computed(() => {
  return Object.keys(sortedPeers.value).length
})

// Fetch health status
function fetchHealthStatus() {
  fetchGet('/api/health/status', {}, (response) => {
    if (response && response.status) {
      healthData.value = response.data
    }
  })
}

// Toggle monitor on/off
function toggleMonitor() {
  loading.value = true
  const endpoint = healthData.value.running ? '/api/health/stop' : '/api/health/start'
  fetchPost(endpoint, {}, () => {
    fetchHealthStatus()
    loading.value = false
  })
}

// Force a check cycle
function forceCycle() {
  loading.value = true
  fetchPost('/api/health/cycle', {}, () => {
    fetchHealthStatus()
    loading.value = false
  })
}

// Ping specific peer
function pingPeer(publicKey) {
  loading.value = true
  fetchPost(`/api/health/peer/${encodeURIComponent(publicKey)}/ping`, {}, () => {
    fetchHealthStatus()
    loading.value = false
  })
}

// Toggle interface monitoring
function toggleInterface(iface, enabled) {
  updateInterfaceConfig(iface, 'enabled', enabled)
}

// Update interface configuration
function updateInterfaceConfig(iface, key, value) {
  fetchPost(`/api/health/config/${iface}`, { [key]: value }, () => {
    fetchHealthStatus()
  })
}

// Helper functions
function getStatusBadgeClass(status) {
  const classes = {
    'online': 'bg-success',
    'unpingable': 'bg-info text-dark',
    'recent': 'bg-warning text-dark',
    'offline': 'bg-danger',
    'unknown': 'bg-secondary'
  }
  return classes[status] || 'bg-secondary'
}

function getStatusLabel(status) {
  const labels = {
    'online': 'online',
    'unpingable': 'unpingable',
    'recent': 'recent',
    'offline': 'offline',
    'unknown': 'unknown'
  }
  return labels[status] || status
}

function getPingableIcon(peer) {
  if (peer.status === 'offline' || peer.status === 'unknown') {
    return 'bi-dash text-muted'
  }
  if (peer.status === 'unpingable') {
    return 'bi-shield-x text-info'
  }
  return peer.is_pingable ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'
}

function getSuccessRateClass(rate) {
  if (rate >= 80) return 'bg-success'
  if (rate >= 50) return 'bg-warning'
  return 'bg-danger'
}

function formatTime(isoTime) {
  if (!isoTime) return '-'
  const date = new Date(isoTime)
  return date.toLocaleTimeString()
}

function formatDateTime(isoTime) {
  if (!isoTime) return '-'
  const date = new Date(isoTime)
  return date.toLocaleString()
}

// Lifecycle
onMounted(() => {
  fetchHealthStatus()
  // Refresh every 10 seconds
  refreshInterval = setInterval(fetchHealthStatus, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.peerHealthMonitor {
  padding: 1rem;
}

.table code {
  background: rgba(0,0,0,0.3);
  padding: 2px 6px;
  border-radius: 4px;
}

.progress {
  background-color: rgba(255,255,255,0.1);
}
</style>
