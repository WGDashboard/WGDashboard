<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	data: Object
})

const cores = computed(() => props.data?.cpu_frequencies || [])
const avg = computed(() => {
	if (!cores.value.length) return 0
	return Math.round(cores.value.reduce((sum, c) => sum + (c.current || 0), 0) / cores.value.length)
})
const barWidth = (core) => {
	const max = core.max || 1
	return Math.min(100, Math.round((core.current / max) * 100)) + '%'
}
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-lightning-charge me-2"></i>
					<LocaleText t="CPU Frequency"></LocaleText>
				</h3>
				<h6 class="ms-auto mb-0 text-muted small">~{{ avg }} MHz</h6>
			</div>
			<div class="freq-grid">
				<div class="freq-pill" v-for="core in cores" :key="core.core">
					<div class="text-muted freq-label">C{{ core.core }}</div>
					<div class="fw-semibold text-body freq-value">{{ Math.round(core.current) }}</div>
					<div class="progress freq-bar" role="progressbar">
						<div class="progress-bar bg-primary" :style="{width: barWidth(core)}"></div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.freq-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(62px, 1fr));
	gap: 0.5rem;
}

.freq-pill {
	background: var(--bs-tertiary-bg);
	border: 1px solid var(--bs-border-color);
	border-radius: 0.4rem;
	padding: 0.4rem 0.25rem 0.5rem;
	text-align: center;
}

.freq-label {
	font-size: 0.65rem;
	line-height: 1;
}

.freq-value {
	font-size: 0.85rem;
	line-height: 1.3;
}

.freq-bar {
	height: 3px;
	margin-top: 0.3rem;
	background: var(--bs-secondary-bg);
}
</style>
