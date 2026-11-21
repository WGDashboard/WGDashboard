<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	data: Object
})

const la = computed(() => props.data?.load_average || {})
const percent = computed(() => la.value.load_percent || 0)
const barClass = computed(() => {
	if (percent.value >= 80) return 'bg-danger'
	if (percent.value >= 50) return 'bg-warning'
	return 'bg-success'
})
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-speedometer2 me-2"></i>
					<LocaleText t="Load Average"></LocaleText>
				</h3>
				<h6 class="ms-auto mb-0 text-muted small">
					{{ la.cpu_count }} <LocaleText t="cores"></LocaleText>
				</h6>
			</div>
			<div class="row text-center g-2 mb-4">
				<div class="col-4">
					<div class="fs-2 fw-bold text-body">{{ la.one_minute ?? '—' }}</div>
					<div class="text-muted small"><LocaleText t="1 min"></LocaleText></div>
				</div>
				<div class="col-4">
					<div class="fs-2 fw-bold text-body">{{ la.five_minutes ?? '—' }}</div>
					<div class="text-muted small"><LocaleText t="5 min"></LocaleText></div>
				</div>
				<div class="col-4">
					<div class="fs-2 fw-bold text-body">{{ la.fifteen_minutes ?? '—' }}</div>
					<div class="text-muted small"><LocaleText t="15 min"></LocaleText></div>
				</div>
			</div>
			<div class="d-flex justify-content-between text-muted small mb-1">
				<span><LocaleText t="Load"></LocaleText></span>
				<span>{{ percent }}%</span>
			</div>
			<div class="progress" role="progressbar" style="height: 8px">
				<div class="progress-bar" :class="barClass" :style="{width: Math.min(percent, 100) + '%'}"></div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.progress-bar {
	transition: width 1s cubic-bezier(0.42, 0, 0.22, 1.0);
}
</style>
