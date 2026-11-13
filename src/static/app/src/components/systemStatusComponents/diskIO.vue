<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	data: Object
})

const disks = computed(() => {
	const rt = props.data?.realtime || {}
	return Object.keys(rt).sort()
})

const fmt = (v) => (Number(v) || 0).toFixed(2)
const barWidth = (v) => Math.min(100, Math.round(((Number(v) || 0) / 500) * 100)) + '%'
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-hdd-stack me-2"></i>
					<LocaleText t="Disk I/O"></LocaleText>
				</h3>
				<h6 class="ms-auto mb-0 text-muted small">{{ disks.length }} <LocaleText t="disks"></LocaleText></h6>
			</div>
			<div class="d-flex flex-column gap-3">
				<div class="disk-item" v-for="disk in disks" :key="disk">
					<div class="fw-semibold text-body font-monospace mb-2">{{ disk }}</div>
					<div class="mb-2">
						<div class="d-flex justify-content-between small mb-1">
							<span class="text-muted"><i class="bi bi-arrow-down-circle me-1"></i><LocaleText t="Read"></LocaleText></span>
							<span class="fw-semibold text-body">{{ fmt(data.realtime[disk].read_mb_s) }} MB/s <span class="text-muted">({{ data.realtime[disk].read_iops }} IOPS)</span></span>
						</div>
						<div class="progress" role="progressbar" style="height: 6px">
							<div class="progress-bar bg-primary" :style="{width: barWidth(data.realtime[disk].read_mb_s)}"></div>
						</div>
					</div>
					<div>
						<div class="d-flex justify-content-between small mb-1">
							<span class="text-muted"><i class="bi bi-arrow-up-circle me-1"></i><LocaleText t="Write"></LocaleText></span>
							<span class="fw-semibold text-body">{{ fmt(data.realtime[disk].write_mb_s) }} MB/s <span class="text-muted">({{ data.realtime[disk].write_iops }} IOPS)</span></span>
						</div>
						<div class="progress" role="progressbar" style="height: 6px">
							<div class="progress-bar bg-warning" :style="{width: barWidth(data.realtime[disk].write_mb_s)}"></div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.disk-item {
	background: var(--bs-tertiary-bg);
	border: 1px solid var(--bs-border-color);
	border-radius: 0.5rem;
	padding: 1rem;
}

.progress {
	background: var(--bs-secondary-bg);
}
</style>
