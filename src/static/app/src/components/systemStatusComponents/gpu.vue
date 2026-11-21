<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	gpu: Object
})

const nvidia = computed(() => props.gpu?.nvidia || [])
const amd = computed(() => props.gpu?.amd || [])
const hasGPU = computed(() => nvidia.value.length > 0 || amd.value.length > 0)

const num = (v) => {
	const n = Number(v)
	return Number.isFinite(n) ? n : 0
}

const utilClass = (u) => {
	if (u >= 90) return 'bg-danger'
	if (u >= 70) return 'bg-warning'
	return 'bg-success'
}

const memPercent = (gpu) => {
	const total = num(gpu.memory_total)
	if (!total) return 0
	return Math.min(100, Math.round((num(gpu.memory_used) / total) * 100))
}

const tempClass = (t) => {
	if (t >= 85) return 'text-bg-danger'
	if (t >= 70) return 'text-bg-warning'
	return 'text-bg-success'
}
</script>

<template>
	<div class="card rounded-3 h-100 shadow" v-if="hasGPU">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-gpu-card me-2"></i>
					<LocaleText t="GPU"></LocaleText>
				</h3>
				<h6 class="ms-auto mb-0 text-muted small">{{ nvidia.length + amd.length }} <LocaleText t="devices"></LocaleText></h6>
			</div>
			<div class="gpu-grid">
				<!-- NVIDIA -->
				<div class="gpu-item" v-for="gpu in nvidia" :key="'n' + gpu.index">
					<div class="d-flex align-items-center mb-3">
						<div class="me-auto">
							<div class="fw-semibold text-body">{{ gpu.name }}</div>
							<div class="text-muted small">#{{ gpu.index }}</div>
						</div>
						<span class="badge temperature" :class="tempClass(num(gpu.temperature))">{{ num(gpu.temperature).toFixed(0) }}°C</span>
						<span class="badge text-bg-success ms-2">NVIDIA</span>
					</div>
					<div class="mb-2">
						<div class="d-flex justify-content-between small mb-1">
							<span class="text-muted"><LocaleText t="GPU Util."></LocaleText></span>
							<span class="fw-semibold text-body">{{ num(gpu.gpu_utilization).toFixed(0) }}%</span>
						</div>
						<div class="progress" role="progressbar" style="height: 6px">
							<div class="progress-bar" :class="utilClass(num(gpu.gpu_utilization))" :style="{width: Math.min(num(gpu.gpu_utilization), 100) + '%'}"></div>
						</div>
					</div>
					<div class="mb-2">
						<div class="d-flex justify-content-between small mb-1">
							<span class="text-muted"><LocaleText t="Memory"></LocaleText></span>
							<span class="fw-semibold text-body">{{ num(gpu.memory_used).toFixed(0) }} / {{ num(gpu.memory_total).toFixed(0) }} MB</span>
						</div>
						<div class="progress" role="progressbar" style="height: 6px">
							<div class="progress-bar bg-info" :style="{width: memPercent(gpu) + '%'}"></div>
						</div>
					</div>
					<div class="d-flex justify-content-between small">
						<span class="text-muted"><LocaleText t="Power"></LocaleText></span>
						<span class="fw-semibold text-body">{{ num(gpu.power_draw).toFixed(0) }} / {{ num(gpu.power_limit).toFixed(0) }} W</span>
					</div>
				</div>
				<!-- AMD -->
				<div class="gpu-item" v-for="gpu in amd" :key="'a' + gpu.index">
					<div class="d-flex align-items-center mb-3">
						<div class="me-auto">
							<div class="fw-semibold text-body">{{ gpu.name || 'GPU #' + gpu.index }}</div>
							<div class="text-muted small">#{{ gpu.index }}</div>
						</div>
						<span class="badge text-bg-danger">AMD</span>
					</div>
					<div class="row g-2 small">
						<div class="col-6"><span class="text-muted"><LocaleText t="Temperature"></LocaleText></span><div class="fw-semibold text-body">{{ gpu.temperature || '—' }}</div></div>
						<div class="col-6"><span class="text-muted"><LocaleText t="Power"></LocaleText></span><div class="fw-semibold text-body">{{ gpu.power || '—' }}</div></div>
						<div class="col-6"><span class="text-muted">SCLK</span><div class="fw-semibold text-body">{{ gpu.sclk || '—' }}</div></div>
						<div class="col-6"><span class="text-muted">MCLK</span><div class="fw-semibold text-body">{{ gpu.mclk || '—' }}</div></div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.gpu-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
	gap: 1rem;
}

.gpu-item {
	background: var(--bs-tertiary-bg);
	border: 1px solid var(--bs-border-color);
	border-radius: 0.5rem;
	padding: 1rem;
}

.progress {
	background: var(--bs-secondary-bg);
}

.progress-bar {
	transition: width 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}
</style>
