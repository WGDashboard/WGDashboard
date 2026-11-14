<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({ power: Object });
const p = computed(() => props.power || {});
const hasPower = computed(() => p.value.available === true);

const kwh = (o) => Number(o?.kwh || 0).toFixed(2) + " kWh";
const eur = (o) => "€" + Number(o?.cost || 0).toFixed(2);
const rows = computed(() => [
	{ key: "today", label: "Today", o: p.value.today },
	{ key: "week", label: "Week (7d)", o: p.value.week },
	{ key: "month", label: "Month (30d)", o: p.value.month },
]);

const days = computed(() => p.value.days || []);
const maxDay = computed(() => Math.max(1e-6, ...days.value.map(d => d.kwh)));
const dayBar = (d) => Math.max(3, Math.round((d.kwh / maxDay.value) * 76)) + "px";

const hours = computed(() => p.value.hours_today || []);
const maxHour = computed(() => Math.max(1e-6, ...hours.value.map(h => h.kwh)));
const hourBar = (h) => Math.max(2, Math.round((h.kwh / maxHour.value) * 44)) + "px";
const peak = computed(() => {
	const m = hours.value.reduce((a, b) => (b.kwh > a.kwh ? b : a), { hour: "--", kwh: 0, cost: 0 });
	return m.hour === "--" ? "--" : m.hour + ":00 · " + m.kwh + " kWh";
});
</script>

<template>
	<div class="card rounded-3 shadow" v-if="hasPower">
		<div class="card-body p-4">
			<div class="d-flex align-items-center mb-3">
				<h3 class="text-muted mb-0">
					<i class="bi bi-lightning-charge me-2"></i>
					<LocaleText t="Power / Energy"></LocaleText>
				</h3>
				<span class="badge text-bg-warning ms-auto">{{ Math.round(p.current_w) }} W now</span>
			</div>
			<div class="row g-2 mb-3">
				<div class="col" v-for="r in rows" :key="r.key">
					<div class="card bg-dark border rounded-2 py-2 px-3">
						<div class="text-muted small">{{ r.label }}</div>
						<div class="fw-semibold">{{ kwh(r.o) }}</div>
						<div class="text-success small">{{ eur(r.o) }}</div>
					</div>
				</div>
			</div>
			<div class="d-flex justify-content-between text-muted small mb-1">
				<span>Rate {{ p.rate_eur_kwh }} €/kWh · base {{ p.base_w }} W (est.)</span>
				<span>14 days</span>
			</div>
			<div class="d-flex align-items-end gap-1 mb-3" style="height: 80px">
				<div v-for="d in days" :key="d.date" class="flex-fill"
					 :title="d.date + ' · ' + d.kwh + ' kWh · €' + d.cost">
					<div class="bg-info rounded-top" :style="{height: dayBar(d)}"></div>
				</div>
			</div>
			<div class="d-flex justify-content-between text-muted small mb-1">
				<span>Today by hour (kWh)</span>
				<span>peak {{ peak }}</span>
			</div>
			<div class="d-flex align-items-end gap-1" style="height: 52px">
				<div v-for="h in hours" :key="h.hour" class="flex-fill"
					 :title="h.hour + ':00 · ' + h.kwh + ' kWh · €' + h.cost">
					<div class="bg-warning rounded-top" :style="{height: hourBar(h)}"></div>
				</div>
			</div>
			<div class="d-flex justify-content-between text-muted" style="font-size: 10px">
				<span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
			</div>
		</div>
	</div>
</template>
