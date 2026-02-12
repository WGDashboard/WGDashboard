<script setup>
import {computed, defineComponent, onBeforeUnmount, onMounted, reactive, ref, useTemplateRef, watch} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import { Line, Bar } from 'vue-chartjs'
import {
	Chart,
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement,
	Filler
} from 'chart.js';
Chart.register(
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement,
	Filler
);

import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import dayjs from "dayjs";
import {useRoute, useRouter} from "vue-router";
import {GetLocale} from "@/utilities/locale.js";
const props = defineProps({
	configurationPeers: Array,
	configurationInfo: Object
})

const historySentData = ref({
	timestamp: [],
	data: []
})

const historyReceivedData = ref({
	timestamp: [],
	data: []
})

// Per-peer speed history: { peerId: { name, timestamps: [], recv: [], sent: [] } }
const peerSpeedHistory = ref({})
const peerSpeedColors = [
	'#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1',
	'#20c997', '#fd7e14', '#0dcaf0', '#d63384', '#6610f2',
	'#198754', '#e83e8c', '#17a2b8', '#28a745', '#007bff'
]
// Current per-peer speed snapshot
const currentPeerSpeed = ref({})

const route = useRoute()
const dashboardStore = DashboardConfigurationStore()
const fetchRealtimeTrafficInterval = ref(undefined)
const fetchRealtimeTraffic = async () => {
	await fetchGet("/api/getWireguardConfigurationRealtimeTraffic", {
		configurationName: route.params.id
	}, (res) => {
		let timestamp = dayjs().format("hh:mm:ss A")
		if (res.data.sent !== 0 && res.data.recv !== 0){
			historySentData.value.timestamp.push(timestamp)
			historySentData.value.data.push(res.data.sent)

			historyReceivedData.value.timestamp.push(timestamp)
			historyReceivedData.value.data.push(res.data.recv)
		}else{
			if (historySentData.value.data.length > 0 && historyReceivedData.value.data.length > 0){
				historySentData.value.timestamp.push(timestamp)
				historySentData.value.data.push(res.data.sent)

				historyReceivedData.value.timestamp.push(timestamp)
				historyReceivedData.value.data.push(res.data.recv)
			}
		}
	})
}

const fetchPeerSpeedInterval = ref(undefined)
const MAX_PEER_SPEED_POINTS = 30
const fetchPeerSpeed = async () => {
	await fetchGet("/api/getWireguardConfigurationPeersRealtimeSpeed", {
		configurationName: route.params.id
	}, (res) => {
		if (!res.status || !res.data) return
		const timestamp = dayjs().format("hh:mm:ss A")
		currentPeerSpeed.value = res.data

		for (const [peerId, info] of Object.entries(res.data)) {
			if (!peerSpeedHistory.value[peerId]) {
				peerSpeedHistory.value[peerId] = {
					name: info.name || peerId.substring(0, 8) + '...',
					timestamps: [],
					recv: [],
					sent: []
				}
			}
			const h = peerSpeedHistory.value[peerId]
			h.name = info.name || peerId.substring(0, 8) + '...'
			h.timestamps.push(timestamp)
			h.recv.push(info.recv)
			h.sent.push(info.sent)
			// Trim to max points
			if (h.timestamps.length > MAX_PEER_SPEED_POINTS) {
				h.timestamps.shift()
				h.recv.shift()
				h.sent.shift()
			}
		}
	})
}

const toggleFetchRealtimeTraffic = () => {
	clearInterval(fetchRealtimeTrafficInterval.value)
	clearInterval(fetchPeerSpeedInterval.value)
	fetchRealtimeTrafficInterval.value = undefined;
	fetchPeerSpeedInterval.value = undefined;
	if (props.configurationInfo.Status){
		const interval = parseInt(dashboardStore.Configuration.Server.dashboard_refresh_interval)
		fetchRealtimeTrafficInterval.value = setInterval(() => {
			fetchRealtimeTraffic()
		}, interval)
		fetchPeerSpeedInterval.value = setInterval(() => {
			fetchPeerSpeed()
		}, interval)
	}
}

onMounted(() => {
	toggleFetchRealtimeTraffic()
})

watch(() => props.configurationInfo.Status, () => {
	toggleFetchRealtimeTraffic()
})

watch(() => dashboardStore.Configuration.Server.dashboard_refresh_interval, () => {
	toggleFetchRealtimeTraffic()
})

onBeforeUnmount(() => {
	clearInterval(fetchRealtimeTrafficInterval.value)
	clearInterval(fetchPeerSpeedInterval.value)
	fetchRealtimeTrafficInterval.value = undefined;
	fetchPeerSpeedInterval.value = undefined;
})

const peersDataUsageChartData = computed(() => {
	let data = props.configurationPeers.filter(x => (x.cumu_data + x.total_data) > 0)
	
	return {
		labels: data.map(x => {
			if (x.name) return x.name
			return `Untitled Peer - ${x.id}`
		}),
		datasets: [{
			label: 'Total Data Usage',
			data: data.map(x => x.cumu_data + x.total_data),
			backgroundColor: data.map(x => `#ffc107`),
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.formattedValue} GB`
					}
				}
			}
		}]
	}
})

// Per-peer current speed bar chart
const peerSpeedBarData = computed(() => {
	const entries = Object.entries(currentPeerSpeed.value)
	if (entries.length === 0) return { labels: [], datasets: [] }

	const labels = entries.map(([id, info]) => info.name || id.substring(0, 8) + '...')
	const recvData = entries.map(([id, info]) => info.recv)
	const sentData = entries.map(([id, info]) => info.sent)

	return {
		labels,
		datasets: [
			{
				label: GetLocale('Received'),
				data: recvData,
				backgroundColor: '#0d6efd90',
				borderColor: '#0d6efd',
				borderWidth: 1,
			},
			{
				label: GetLocale('Sent'),
				data: sentData,
				backgroundColor: '#19875490',
				borderColor: '#198754',
				borderWidth: 1,
			}
		]
	}
})

// Per-peer speed line chart - Received
const peerSpeedRecvLineData = computed(() => {
	const peerIds = Object.keys(peerSpeedHistory.value)
	if (peerIds.length === 0) return { labels: [], datasets: [] }

	// Use timestamps from the first peer (all should be in sync)
	const firstPeer = peerSpeedHistory.value[peerIds[0]]
	const labels = firstPeer ? [...firstPeer.timestamps] : []

	const datasets = peerIds.map((peerId, idx) => {
		const h = peerSpeedHistory.value[peerId]
		const color = peerSpeedColors[idx % peerSpeedColors.length]
		return {
			label: h.name,
			data: [...h.recv],
			borderColor: color,
			backgroundColor: color + '40',
			fill: false,
			tension: 0.2,
			pointRadius: 1,
			borderWidth: 2,
		}
	})

	return { labels, datasets }
})

// Per-peer speed line chart - Sent
const peerSpeedSentLineData = computed(() => {
	const peerIds = Object.keys(peerSpeedHistory.value)
	if (peerIds.length === 0) return { labels: [], datasets: [] }

	const firstPeer = peerSpeedHistory.value[peerIds[0]]
	const labels = firstPeer ? [...firstPeer.timestamps] : []

	const datasets = peerIds.map((peerId, idx) => {
		const h = peerSpeedHistory.value[peerId]
		const color = peerSpeedColors[idx % peerSpeedColors.length]
		return {
			label: h.name,
			data: [...h.sent],
			borderColor: color,
			backgroundColor: color + '40',
			fill: false,
			tension: 0.2,
			pointRadius: 1,
			borderWidth: 2,
		}
	})

	return { labels, datasets }
})

const peersRealtimeSentData = computed(() => {
	return {
		labels: [...historySentData.value.timestamp],
		datasets: [
			{
				label: GetLocale('Data Sent'),
				data: [...historySentData.value.data],
				fill: 'start',
				borderColor: '#198754',
				backgroundColor: '#19875490',
				tension: 0,
				pointRadius: 2,
				borderWidth: 1,
			},
		],
	}
})
const peersRealtimeReceivedData = computed(() => {
	return {
		labels: [...historyReceivedData.value.timestamp],
		datasets: [
			{
				label: GetLocale('Data Received'),
				data: [...historyReceivedData.value.data],
				fill: 'start',
				borderColor: '#0d6efd',
				backgroundColor: '#0d6efd90',
				tension: 0,
				pointRadius: 2,
				borderWidth: 1,
			},
		],
	}
})


const peersDataUsageChartOption = computed(() => {
	return {
		responsive: true,
		plugins: {
			legend: {
				display: false
			}
		},
		scales: {
			x: {
				ticks: {
					display: false,
				},
				grid: {
					display: false
				},
			},
			y:{
				ticks: {
					callback: (val, index) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} GB`
					}
				},
				grid: {
					display: false
				},
			}
		}
	}
})

const peerSpeedBarOption = computed(() => {
	return {
		responsive: true,
		plugins: {
			legend: {
				display: true,
				position: 'top',
				labels: { boxWidth: 12 }
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.dataset.label}: ${tooltipItem.formattedValue} MB/s`
					}
				}
			}
		},
		scales: {
			x: {
				ticks: {
					display: false,
				},
				grid: {
					display: false
				},
			},
			y:{
				ticks: {
					callback: (val) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} MB/s`
					}
				},
				grid: {
					display: false
				},
			}
		}
	}
})

const realtimePeersChartOption = computed(() => {
	return {
		responsive: true,
		plugins: {
			legend: {
				display: false
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.formattedValue} MB/s`
					}
				}
			}
		},
		scales: {
			x: {
				ticks: {
					display: false,
				},
				grid: {
					display: true
				},
			},
			y:{
				ticks: {
					callback: (val, index) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} MB/s`
					}
				},
				grid: {
					display: true
				},
			}
		}
	}
})

const perPeerLineChartOption = computed(() => {
	return {
		responsive: true,
		interaction: {
			mode: 'index',
			intersect: false
		},
		plugins: {
			legend: {
				display: true,
				position: 'top',
				labels: {
					boxWidth: 12,
					font: { size: 10 }
				}
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.dataset.label}: ${tooltipItem.formattedValue} MB/s`
					}
				}
			}
		},
		scales: {
			x: {
				ticks: {
					display: false,
				},
				grid: {
					display: true
				},
			},
			y: {
				ticks: {
					callback: (val) => {
						return `${Math.round((val + Number.EPSILON) * 1000) / 1000} MB/s`
					}
				},
				grid: {
					display: true
				},
			}
		}
	}
})

const hasPeerSpeedData = computed(() => {
	return Object.keys(currentPeerSpeed.value).length > 0
})
</script>

<template>
	<div class="row gx-2 gy-2 mb-3">
		<div class="col-12">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0">
					<small class="text-muted">
						<LocaleText t="Peers Data Usage"></LocaleText>
					</small></div>
				<div class="card-body pt-1">
					<Bar
						:data="peersDataUsageChartData"
						:options="peersDataUsageChartOption"
						style="width: 100%; height: 200px;  max-height: 200px"></Bar>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Real Time Received Data Usage"></LocaleText>
					</small>
					<small class="text-primary fw-bold ms-auto" v-if="historyReceivedData.data.length > 0">
						{{historyReceivedData.data[historyReceivedData.data.length - 1]}} MB/s
					</small>
				</div>
				<div class="card-body pt-1">
					<Line
						:options="realtimePeersChartOption"
						:data="peersRealtimeReceivedData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6">
			<div class="card rounded-3 bg-transparent " style="height: 270px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Real Time Sent Data Usage"></LocaleText>
					</small>
					<small class="text-success fw-bold ms-auto"  v-if="historySentData.data.length > 0">
						{{historySentData.data[historySentData.data.length - 1]}} MB/s
					</small>
				</div>
				<div class="card-body  pt-1">
					<Line
						:options="realtimePeersChartOption"
						:data="peersRealtimeSentData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
				</div>
			</div>
		</div>

		<!-- Per-Peer Bandwidth Monitoring -->
		<div class="col-12" v-if="hasPeerSpeedData">
			<div class="card rounded-3 bg-transparent" style="height: 300px">
				<div class="card-header bg-transparent border-0">
					<small class="text-muted">
						<i class="bi bi-speedometer2 me-1"></i>
						<LocaleText t="Per-Peer Current Speed"></LocaleText>
					</small>
				</div>
				<div class="card-body pt-1">
					<Bar
						:data="peerSpeedBarData"
						:options="peerSpeedBarOption"
						style="width: 100%; height: 220px; max-height: 220px"
					></Bar>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6" v-if="hasPeerSpeedData">
			<div class="card rounded-3 bg-transparent" style="height: 300px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<i class="bi bi-arrow-down me-1"></i>
						<LocaleText t="Per-Peer Received Speed"></LocaleText>
					</small>
				</div>
				<div class="card-body pt-1">
					<Line
						:options="perPeerLineChartOption"
						:data="peerSpeedRecvLineData"
						style="width: 100%; height: 220px; max-height: 220px"
					></Line>
				</div>
			</div>
		</div>
		<div class="col-sm col-lg-6" v-if="hasPeerSpeedData">
			<div class="card rounded-3 bg-transparent" style="height: 300px">
				<div class="card-header bg-transparent border-0 d-flex align-items-center">
					<small class="text-muted">
						<i class="bi bi-arrow-up me-1"></i>
						<LocaleText t="Per-Peer Sent Speed"></LocaleText>
					</small>
				</div>
				<div class="card-body pt-1">
					<Line
						:options="perPeerLineChartOption"
						:data="peerSpeedSentLineData"
						style="width: 100%; height: 220px; max-height: 220px"
					></Line>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>