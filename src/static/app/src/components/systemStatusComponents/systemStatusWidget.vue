<script setup>
import {computed, onBeforeUnmount, onMounted, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import CpuCore from "@/components/systemStatusComponents/cpuCore.vue";
import StorageMount from "@/components/systemStatusComponents/storageMount.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const dashboardStore = DashboardConfigurationStore()
let interval = null;

onMounted(() => {
	getData()
	interval = setInterval(() => {
		getData()
	}, 5000)
})

onBeforeUnmount(() => {
	clearInterval(interval)
})

const getData = () => {
	fetchGet("/api/systemStatus", {}, (res) => {
		dashboardStore.SystemStatus = res.data
	})
}

const data = computed(() => {
	return dashboardStore.SystemStatus
})
</script>

<template>
	<div class="row text-body g-3 mb-5">
		<div class="col-md-6 col-sm-12 col-xl-3">
			<div class="d-flex align-items-center">
				<h6 class="text-muted">
					<i class="bi bi-cpu-fill me-2"></i>
					<LocaleText t="CPU"></LocaleText>
				</h6>
				<h6 class="ms-auto">
					<span v-if="data">
						{{ data.CPU.cpu_percent }}%
					</span>
					<span v-else class="spinner-border spinner-border-sm"></span>
				</h6>
			</div>
			<div class="progress" role="progressbar" style="height: 6px">
				<div class="progress-bar" :style="{width: `${data?.CPU.cpu_percent}%` }"></div>
			</div>
			<div class="d-flex mt-2 gap-1">
				<CpuCore
					v-for="(cpu, count) in data?.CPU.cpu_percent_per_cpu"
				         :key="count"
				         :align="(count + 1) > Math.round(data?.CPU.cpu_percent_per_cpu.length / 2)"
				         :core_number="count" :percentage="cpu"
				></CpuCore>
			</div>
		</div>
		<div class="col-md-6 col-sm-12 col-xl-3">
			<div class="d-flex align-items-center">
				<h6 class="text-muted">
					<i class="bi bi-device-ssd-fill me-2"></i>
					<LocaleText t="Storage"></LocaleText>
				</h6>
				<h6 class="ms-auto">
					<span v-if="data">
						{{ data.Disks.find(x => x.mountPoint === '/') ? data?.Disks.find(x => x.mountPoint === '/').percent : data?.Disks[0].percent }}%
					</span>
					<span v-else class="spinner-border spinner-border-sm"></span>
				</h6>
			</div>
			<div class="progress" role="progressbar" style="height: 6px">
				<div class="progress-bar bg-success" :style="{width: `${data?.Disks.find(x => x.mountPoint === '/') ? data?.Disks.find(x => x.mountPoint === '/').percent : data?.Disks[0].percent}%` }"></div>
			</div>
			<div class="d-flex mt-2 gap-1">
				<StorageMount v-for="(disk, count) in data?.Disks"
				              v-if="data"
				              :key="disk.mountPoint"
				              :align="(count + 1) > Math.round(data?.Disks.length / 2)"
				              :mount="disk"
				></StorageMount>
			</div>
		</div>
		<div class="col-md-6 col-sm-12 col-xl-3">
			<div class="d-flex align-items-center">
				<h6 class="text-muted">
					<i class="bi bi-memory me-2"></i>
					<LocaleText t="Memory"></LocaleText>
				</h6>
				<h6 class="ms-auto">
							<span v-if="data">
								{{ data?.Memory.VirtualMemory.percent }}%
							</span>
					<span v-else class="spinner-border spinner-border-sm"></span>
				</h6>
			</div>
			<div class="progress" role="progressbar" style="height: 6px">
				<div class="progress-bar bg-info" :style="{width: `${data?.Memory.VirtualMemory.percent}%` }"></div>
			</div>
		</div>
		<div class="col-md-6 col-sm-12 col-xl-3">
			<div class="d-flex align-items-center">
				<h6 class="text-muted">
					<i class="bi bi-memory me-2"></i>
					<LocaleText t="Swap Memory"></LocaleText>
				</h6>
				<h6 class="ms-auto">
							<span v-if="data">
								{{ data?.Memory.SwapMemory.percent }}%
							</span>
					<span v-else class="spinner-border spinner-border-sm"></span>
				</h6>
			</div>
			<div class="progress" role="progressbar" style="height: 6px">
				<div class="progress-bar bg-warning" :style="{width: `$ data?.Memory.SwapMemory.percent}%` }"></div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.progress-bar {
	width: 0;
	transition: all 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}
</style>