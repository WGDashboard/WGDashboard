<script setup>
import {computed, ref} from "vue";
import ConfigurationQRCode from "@/components/Configuration/configurationQRCode.vue";
import dayjs from "dayjs";
import Duration from 'dayjs/plugin/Duration'
dayjs.extend(Duration);
const props = defineProps([
	'config'
])
const showQRCode = ref(false)

const dateJobs = computed(() => {
	return props.config.jobs.filter(x => x.Field === 'date').sort((x, y) => {
		if (dayjs(x.Value).isBefore(y.Value)){
			return -1
		}else if (dayjs(x.Value).isAfter(y.Value)){
			return 1
		}else{
			return 0
		}
	})
});

const totalDataJobs = computed(() => {
	return props.config.jobs.filter(x => x.Field === "total_data").sort((x, y) => {
		return parseFloat(y.Value) - parseFloat(x.Value)
	})
});

const dateLimit = computed(() => {
	if (dateJobs.value.length > 0){
		return dateJobs.value[0].Value
	}
	return undefined
})
const totalDataLimit = computed(() => {
	if (totalDataJobs.value.length > 0){
		return totalDataJobs.value[0].Value
	}
	return undefined
})

const totalDataPercentage = computed(() => {
	if (!totalDataLimit.value) return 100
	return ( props.config.data / totalDataLimit.value ) * 100
})
window.dayjs = dayjs
</script>

<template>
	<div class="card rounded-3 border-0 shadow">
		<div class="card-header rounded-top-3 border-0 align-items-center d-flex p-3 flex-column flex-sm-row gap-2">
			<small class="fw-bold">
				{{ props.config.name }}
			</small>
			<span class="badge rounded-3 ms-sm-auto"
			      :class="[props.config.protocol === 'wg' ? 'wireguardBg' : 'amneziawgBg' ]"
			      v-if="props.config.protocol === 'wg'">
							{{ props.config.protocol === 'wg' ? 'WireGuard': 'AmneziaWG' }}
						</span>
		</div>
		<div class="card-body p-3 d-flex gap-3 flex-column">
			<div>
				<div class="mb-1 d-flex align-items-center">
					<small class="text-muted ">
						<i class="bi bi-bar-chart-fill me-1"></i> Data Usage
					</small>
					<small class="fw-bold ms-sm-auto">
						{{ props.config.data.toFixed(4) }} / {{ totalDataLimit ? parseFloat(totalDataLimit).toFixed(4) : 'Unlimited'}} GB
					</small>
				</div>
				<div class="progress" role="progressbar" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100" style="height: 6px">
					<div class="progress-bar bg-primary"
					     :style="{'width': '' + totalDataPercentage + '%'}"></div>
				</div>
			</div>
			<div>
				<div class="mb-1 d-flex align-items-center">
					<small class="text-muted">
						<i class="bi bi-calendar me-1"></i> Valid Until
					</small>
					<small class="fw-bold ms-auto">
						{{ dateLimit ? dateLimit : 'Unlimited Time' }}
					</small>
				</div>
			</div>

			<button class="btn btn-outline-body rounded-3 flex-grow-1 fw-bold w-100" @click="showQRCode = true">
				<i class="bi bi-link-45deg me-2"></i><small>Connect</small>
			</button>
		</div>
		<Transition name="app">
			<ConfigurationQRCode
				v-if="showQRCode"
				@back="showQRCode = false"
				:qrcode-data="config.peer_configuration_data.file"></ConfigurationQRCode>
		</Transition>
	</div>
</template>

<style scoped>
.button-group a:hover{
	background-color: #ffffff20;
}

.dot{
	width: 10px;
	height: 10px;
	border-radius: 50px;
	display: inline-block;
	margin-left: auto !important;
	background-color: #6c757d;
}

.dot.active {
	background-color: #28a745 !important;
	box-shadow: 0 0 0 .2rem #28a74545;
}
</style>