<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	data: Object
})

const info = computed(() => props.data || {})
const bootTime = computed(() => {
	if (!info.value.boot_time) return '—'
	return new Date(info.value.boot_time * 1000).toLocaleString()
})
</script>

<template>
	<div class="card rounded-3 h-100 shadow">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-4">
				<h3 class="text-muted mb-0">
					<i class="bi bi-pc-display me-2"></i>
					<LocaleText t="System Information"></LocaleText>
				</h3>
			</div>
			<div class="row g-4">
				<div class="col-sm-6">
					<div class="text-muted small mb-1"><LocaleText t="Hostname"></LocaleText></div>
					<div class="fw-semibold text-body font-monospace text-truncate">{{ info.hostname || '—' }}</div>
				</div>
				<div class="col-sm-6">
					<div class="text-muted small mb-1"><LocaleText t="Uptime"></LocaleText></div>
					<div class="fw-semibold text-body font-monospace">{{ info.uptime_formatted || '—' }}</div>
				</div>
				<div class="col-12">
					<div class="text-muted small mb-1"><LocaleText t="Boot Time"></LocaleText></div>
					<div class="fw-semibold text-body">{{ bootTime }}</div>
				</div>
			</div>
		</div>
	</div>
</template>
