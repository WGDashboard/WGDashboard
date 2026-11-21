<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	temperatures: Object
})

const DEVICE_ORDER = ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal', 'acpitz', 'nvme', 'amdgpu', 'i915']

const devices = computed(() => {
	const temps = props.temperatures || {}
	return Object.keys(temps)
		.filter((name) => Array.isArray(temps[name]) && temps[name].length)
		.sort((a, b) => {
			const ia = DEVICE_ORDER.indexOf(a.toLowerCase())
			const ib = DEVICE_ORDER.indexOf(b.toLowerCase())
			return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
		})
})

const shortLabel = (label) => {
	if (!label) return '—'
	const core = /^core\s*(\d+)$/i.exec(label.trim())
	if (core) return 'C' + core[1]
	if (/package/i.test(label)) return 'Pkg'
	if (/^tctl$/i.test(label)) return 'Tctl'
	return label
}

const badgeClass = (temp, critical) => {
	if (!temp) return 'text-bg-secondary'
	if (critical && temp >= critical) return 'text-bg-danger'
	if (temp >= 85) return 'text-bg-danger'
	if (temp >= 70) return 'text-bg-warning'
	return 'text-bg-success'
}
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-thermometer-half me-2"></i>
					<LocaleText t="System Temperature"></LocaleText>
				</h3>
			</div>
			<div class="d-flex flex-column gap-3">
				<div v-for="device in devices" :key="device">
					<div class="text-muted text-uppercase fw-semibold small mb-2">{{ device }}</div>
					<div class="d-flex flex-wrap gap-2">
						<span
							v-for="(temp, idx) in temperatures[device]"
							:key="idx"
							class="badge rounded-pill d-inline-flex align-items-center gap-1"
							:class="badgeClass(temp.current, temp.critical)"
						>
							<span class="opacity-75">{{ shortLabel(temp.label) }}</span>
							<span class="fw-bold">{{ temp.current != null ? temp.current.toFixed(0) : '—' }}°C</span>
						</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
