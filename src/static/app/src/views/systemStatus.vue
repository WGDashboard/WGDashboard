<script setup>
import {computed, onBeforeUnmount, onMounted, reactive, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import CpuCore from "@/components/systemStatusComponents/cpuCore.vue";
import StorageMount from "@/components/systemStatusComponents/storageMount.vue";
import Process from "@/components/systemStatusComponents/process.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const dashboardStore = DashboardConfigurationStore()
const loaded = ref(false)
const data = computed(() => {
	return loaded.value ? dashboardStore.SystemStatus : undefined
})

let interval = null;
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
import {Line} from "vue-chartjs";
import dayjs from "dayjs";
import {GetLocale} from "@/utilities/locale.js";
import NetworkInterface from "@/components/systemStatusComponents/networkInterface.vue";
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

onMounted(() => {
	getData()
	interval = setInterval(() => {
		getData()
	}, 5000)
})

onBeforeUnmount(() => {
	clearInterval(interval)
})

const historicalChartTimestamp = ref([])
const historicalCpuUsage = ref([])
const historicalVirtualMemoryUsage = ref([])
const historicalSwapMemoryUsage = ref([])
const historicalNetworkSpeed = reactive({})

const getData = async () => {
	await fetchGet("/api/systemStatus", {}, (res) => {
		historicalChartTimestamp.value.push(dayjs().format("HH:mm:ss A"))
		dashboardStore.SystemStatus = res.data
		historicalCpuUsage.value.push(res.data.CPU.cpu_percent)
		historicalVirtualMemoryUsage.value.push(res.data.Memory.VirtualMemory.percent)
		historicalSwapMemoryUsage.value.push(res.data.Memory.SwapMemory.percent)

		for (let i of Object.keys(res.data.NetworkInterfaces)){
			if (!Object.keys(historicalNetworkSpeed).includes(i)){
				historicalNetworkSpeed[i] = {
					bytes_recv: [],
					bytes_sent: []
				}
			}
			historicalNetworkSpeed[i].bytes_recv.push(res.data.NetworkInterfaces[i].realtime.recv)
			historicalNetworkSpeed[i].bytes_sent.push(res.data.NetworkInterfaces[i].realtime.sent)
		}
		loaded.value = true
	})
}

const chartOption = computed(() => {
	return {
		responsive: true,
		plugins: {
			legend: {
				display: true
			},
			tooltip: {
				callbacks: {
					label: (tooltipItem) => {
						return `${tooltipItem.formattedValue}%`
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
					callback: (val, index) => {
						return `${val}%`
					}
				},
				grid: {
					display: false
				},
			}
		}
	}
})
const cpuHistoricalChartData = computed(() => {
	return {
		labels: [...historicalChartTimestamp.value],
		datasets: [
			{
				label: GetLocale('CPU Usage'),
				data: [...historicalCpuUsage.value],
				fill: 'start',
				backgroundColor: '#0d6efd90',
				borderColor: '#0d6efd',
				tension: 0,
				pointRadius: 2,
				borderWidth: 1,
			}
		]
	}
})

const memoryHistoricalChartData = computed(() => {
	return {
		labels: [...historicalChartTimestamp.value],
		datasets: [
			{
				label: GetLocale('Memory Usage'),
				data: [...historicalVirtualMemoryUsage.value],
				fill: 1,
				borderColor: '#0dcaf0',
				backgroundColor: '#0dcaf090',
				tension: 0,
				pointRadius: 2,
				borderWidth: 1,
			},
			{
				label: GetLocale('Swap Memory Usage'),
				data: [...historicalSwapMemoryUsage.value],
				fill: 'start',
				backgroundColor: '#ffc10790',
				borderColor: '#ffc107',
				tension: 0,
				pointRadius: 2,
				borderWidth: 1,
			}
		]
	}
})

</script>

<template>
<div class="text-body row g-2 mb-2">
	<div class="col-sm-6">
		<div class="card rounded-3 h-100 shadow">
			<div class="card-body p-4">
				<div class="d-flex flex-column gap-3">
					<div class="d-flex flex-column gap-3" style="height: 130px">
						<div class="d-flex align-items-center">
							<h3 class="text-muted mb-0">
								<i class="bi bi-cpu-fill me-2"></i>
								<LocaleText t="CPU"></LocaleText>
							</h3>
							<h3 class="ms-auto mb-0">
								<span v-if="data">
									{{ data.CPU.cpu_percent }}%
								</span>
								<span v-else class="spinner-border"></span>
							</h3>
						</div>
						<div class="progress" role="progressbar" style="height: 10px">
							<div class="progress-bar" :style="{width: `${data?.CPU.cpu_percent}%` }"></div>
						</div>
						<div class="d-flex gap-1">
							<CpuCore
								v-for="(cpu, count) in data?.CPU.cpu_percent_per_cpu"
								:square="true"
								:key="count"
								:align="(count + 1) > Math.round(data?.CPU.cpu_percent_per_cpu.length / 2)"
								:core_number="count" :percentage="cpu"
							></CpuCore>
						</div>
					</div>
					<Line
						:options="chartOption"
						:data="cpuHistoricalChartData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
					<div class="d-flex align-items-center">
						<h5 class="mb-0">
							<LocaleText t="Processes"></LocaleText>
						</h5>
						<h6 class="mb-0 ms-auto text-muted">
							<small>
								<LocaleText t="CPU Usage"></LocaleText>
							</small>
						</h6>
						
					</div>
					<hr class="my-1">
					<div class="position-relative">
						<TransitionGroup name="process">
							<Process
								:key="p.pid"
								:cpu="true"
								:process="p" v-for="p in data?.Processes.cpu_top_10"></Process>
						</TransitionGroup>
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="col-sm-6">
		<div class="card rounded-3 h-100 shadow">
			<div class="card-body p-4">
				<div class="d-flex flex-column gap-3">
					<div class="d-flex flex-column gap-3" style="height: 130px">
						<div class="d-flex align-items-center">
							<h3 class="text-muted">
								<i class="bi bi-memory me-2"></i>
								<LocaleText t="Memory"></LocaleText>
							</h3>
							<h3 class="ms-auto">
								<span v-if="data">
									{{ data?.Memory.VirtualMemory.percent }}%
								</span>
								<span v-else class="spinner-border"></span>
							</h3>
						</div>
						<div class="progress" role="progressbar" style="height: 10px">
							<div class="progress-bar bg-info" :style="{width: `${data?.Memory.VirtualMemory.percent}%` }"></div>
						</div>
						<div class="d-flex align-items-center">
							<h6 class="mb-0">
								<LocaleText t="Swap Memory"></LocaleText>
							</h6>
							<h6 class="mb-0 ms-auto">{{data?.Memory.SwapMemory.percent}}%</h6>
						</div>
						<div class="progress" role="progressbar" style="height: 10px">
							<div class="progress-bar bg-info-subtle" :style="{width: `${data?.Memory.SwapMemory.percent}%` }"></div>
						</div>
					</div>
					<Line
						:options="chartOption"
						:data="memoryHistoricalChartData"
						style="width: 100%; height: 200px; max-height: 200px"
					></Line>
					<div class="d-flex align-items-center">
						<h5 class="mb-0">
							<LocaleText t="Processes"></LocaleText>
						</h5>
						<h6 class="mb-0 ms-auto text-muted">
							<small>
								<LocaleText t="Memory Usage"></LocaleText>
							</small>
						</h6>

					</div>
					<hr class="my-1">
					<div class="position-relative">
						<TransitionGroup name="process">
							<Process
								:key="p.pid"
								:process="p" v-for="p in data?.Processes.memory_top_10">
							</Process>
						</TransitionGroup>
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="col-sm-12">
		<div class="card rounded-3 h-100 shadow">
			<div class="card-body p-4 d-flex gap-3 flex-column">
				<div class="d-flex align-items-center gap-3">
					<h3 class="text-muted mb-0">
						<i class="bi bi-ethernet me-2"></i>
						<LocaleText t="Network"></LocaleText>
					</h3>
					
					<h3 class="ms-auto mb-0">
						<span v-if="data">
							<LocaleText :t="Object.keys(data.NetworkInterfaces).length + ' Interface' + (Object.keys(data.NetworkInterfaces).length > 1 ? 's':'')"></LocaleText>
						</span>
						<span v-else class="spinner-border"></span>
					</h3>
				</div>
				<div>
				</div>
				<div v-if="data" class="row g-4">
					<NetworkInterface
						v-for="key in Object.keys(data.NetworkInterfaces).sort()"
						:interface="data.NetworkInterfaces[key]"
						:interfaceName="key"
						:historicalChartTimestamp="historicalChartTimestamp"
						:historicalNetworkSpeed="historicalNetworkSpeed[key]"
						:key="key"
					></NetworkInterface>
				</div>
			</div>
		</div>
	</div>
	<div class="col-sm-12">
		<div class="card rounded-3 h-100 shadow">
			<div class="card-body p-4 d-flex gap-3 flex-column">
				<div class="d-flex align-items-center">
					<h3 class="text-muted mb-0">
						<i class="bi bi-device-ssd-fill me-2"></i>
						<LocaleText t="Storage"></LocaleText>
					</h3>
					<h3 class="ms-auto mb-0">
							<span v-if="data">
								<LocaleText :t="data.Disks.length + ' Partition' + (data.Disks.length > 1 ? 's':'')"></LocaleText>
							</span>
							<span v-else class="spinner-border"></span>
					</h3>
				</div>
				<div class="row g-3">
					<div v-for="disk in data.Disks" class="col-sm-6 fadeIn"
					     v-if="data">
						<div class="d-flex mb-2">
							<h6 class="mb-0">
								<samp>{{disk.mountPoint}}</samp>
							</h6>
							<h6 class="mb-0 ms-auto d-flex gap-2">
								<span class="text-success">
									<LocaleText :t="Math.round((disk.used / 1024000000 + Number.EPSILON) * 100) / 100 + ' / ' + Math.round((disk.total / 1024000000 + Number.EPSILON) * 100) / 100 + ' GB Used'"></LocaleText>
								</span>
							</h6>
						</div>
						<div class="progress" role="progressbar" style="height: 20px">
							<div class="progress-bar bg-success"
							     :style="{width: `${disk.percent}%`}">
								{{ disk.percent }}%
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
	
</div>
</template>

<style scoped>
.process-move, /* apply transition to moving elements */
.process-enter-active,
.process-leave-active {
	transition: all 0.5s cubic-bezier(0.42, 0, 0.22, 1.0);
}

.process-enter-from,
.process-leave-to {
	opacity: 0;
	transform: scale(0.9);
}

.process-leave-active {
	position: absolute;
	width: 100%;
}

.progress-bar {
	width: 0;
	transition: all 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}

.fadeIn{
	opacity: 0;
	animation: fadeIn 0.5s forwards cubic-bezier(0.42, 0, 0.22, 1.0);
}

@keyframes fadeIn {
	from {
		opacity: 0;
		transform: translateY(30px);
	}
	to{
		opacity: 1;
		transform: translateY(0px);
	}
}
</style>