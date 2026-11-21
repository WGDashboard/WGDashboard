<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	fans: Object
})

const devices = computed(() => {
	const fans = props.fans || {}
	return Object.keys(fans).filter((name) => Array.isArray(fans[name]) && fans[name].length).sort()
})

const barWidth = (rpm) => Math.min(100, Math.round(((Number(rpm) || 0) / 6000) * 100)) + '%'

const badgeClass = (rpm) => {
	if (!rpm) return 'text-bg-secondary'
	if (rpm >= 5000) return 'text-bg-danger'
	if (rpm >= 3000) return 'text-bg-warning'
	return 'text-bg-success'
}
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-fan me-2"></i>
					<LocaleText t="Fan Speed"></LocaleText>
				</h3>
			</div>
			<div class="d-flex flex-column gap-3">
				<div v-for="device in devices" :key="device">
					<div class="text-muted text-uppercase fw-semibold small mb-2">{{ device }}</div>
					<div class="d-flex flex-column gap-2">
						<div v-for="(fan, idx) in fans[device]" :key="idx">
							<div class="d-flex justify-content-between align-items-center small mb-1">
								<span class="text-body">{{ fan.label }}</span>
								<span class="fw-semibold text-body">{{ fan.current || 0 }} RPM</span>
							</div>
							<div class="progress" role="progressbar" style="height: 6px">
								<div class="progress-bar" :class="badgeClass(fan.current)" :style="{width: barWidth(fan.current)}"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.progress {
	background: var(--bs-secondary-bg);
}

.progress-bar {
	transition: width 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}
</style>
