<script setup>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {onMounted, ref, watch} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const props = defineProps(['configuration'])
const sizes = ref({
	HistoricalTrackingTableSize: 0,
	TrafficTrackingTableSize: 0
})
const sizeDataLoaded = ref(false)
const toggling = ref(false)

await onMounted(async () => {
	await loadSizeData();
})

const loadSizeData = async () => {
	sizeDataLoaded.value = false;
	await fetchGet("/api/getPeerTrackingTableCounts", {
		configurationName: props.configuration.Name
	}, (res) => {
		sizes.value = res.data;
		sizeDataLoaded.value = true;
	})
}

const updateToggle = async (key) => {
	toggling.value = true;
	await fetchPost('/api/updateWireguardConfigurationInfo', {
		Name: props.configuration.Name,
		Key: key,
		Value: props.configuration.Info[key]
	}, (res) => {
		console.log(res)
		toggling.value = false;
	})
}
const downloading = ref(undefined);
const download = async (key) => {
	downloading.value = key;
	await fetchGet("/api/downloadPeerTrackingTable", {
		configurationName: props.configuration.Name,
		table: key
	}, (res) => {
		if (res.status){
			const s = JSON.stringify(res.data, null, 2)
			const b = new Blob([s], {
				type: "application/json"
			})
			const url = URL.createObjectURL(b)
			const a = document.createElement('a')
			a.href = url;
			a.download = `${props.configuration.Name}_${key}.json`
			a.click()
			downloading.value = undefined;
		}
	})
}

const confirmDelete = ref("")
const deleting = ref(undefined)
const dashboardStore = DashboardConfigurationStore()
const deleteRecord = async (key) => {
	deleting.value = true;
	await fetchPost('/api/deletePeerTrackingTable', {
		configurationName: props.configuration.Name,
		table: key
	}, async(res) => {
		if (res.status){
			dashboardStore.newMessage('Server', 'Record deleted', 'success')
		}else{
			dashboardStore.newMessage('Server', 'Record delete failed', 'danger')
		}
		await loadSizeData()
		deleting.value = false;
		confirmDelete.value = ''
	})
}


</script>

<template>
	<div class="card">
		<div class="card-header">
			{{ configuration.Name }}
		</div>
		<div class="card-body">
			<div class="row gy-2">
				<div class="col-sm">
					<small class="text-muted fw-bold">Peer Traffic Tracking</small>
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox"
							   :disabled="toggling"
							   @change="updateToggle('PeerTrafficTracking')"
							   v-model="configuration.Info.PeerTrafficTracking" :id="configuration.Name + '_traffic_tracking'">
						<label class="form-check-label" :for="configuration.Name + '_traffic_tracking'">
							{{ configuration.Info.PeerTrafficTracking ? 'On':'Off'}}
						</label>
					</div>
					<hr />
					<div class="d-flex align-items-start align-items-md-center flex-column flex-md-row gap-2">
						<h6 class="mb-0">
							{{ sizes.TrafficTrackingTableSize }} <span class="text-muted fw-normal"><LocaleText t="Records"></LocaleText></span>
						</h6>
						<div class="ms-md-auto d-flex gap-2" v-if="confirmDelete !== 'TrafficTrackingTable'">
							<button class="btn btn-sm bg-primary-subtle text-primary-emphasis rounded-3"
									:class="{disabled: downloading === 'TrafficTrackingTable'}"
								@click="download('TrafficTrackingTable')"
							>
								<i class="bi bi-download me-2 "></i>
								<LocaleText :t="downloading === 'TrafficTrackingTable' ? 'Downloading...':'Download'"></LocaleText>
							</button>
							<button class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3" @click="confirmDelete = 'TrafficTrackingTable'">
								<i class="bi bi-trash me-2 "></i>Delete
							</button>
						</div>
						<div class="ms-md-auto d-flex gap-2 align-items-center" v-else-if="confirmDelete === 'TrafficTrackingTable'">
							<small>
								<LocaleText t="Are you sure to delete?"></LocaleText>
							</small>
							<button class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3"
									:class="{disabled: deleting}"
									@click="deleteRecord('TrafficTrackingTable')">
								<i class="bi bi-check me-2 "></i>Yes
							</button>
							<button
								:class="{disabled: deleting}"
								class="btn btn-sm bg-secondary-subtle text-secondary-emphasis rounded-3" @click="confirmDelete = ''">
								<i class="bi bi-x me-2 "></i>No
							</button>
						</div>
					</div>
				</div>
				<div class="col-sm">
					<small class="text-muted fw-bold">Peer Historical Endpoint Tracking</small>
					<div class="form-check form-switch">
						<input class="form-check-input"
							   :disabled="toggling"
							   @change="updateToggle('PeerHistoricalEndpointTracking')"
							   type="checkbox" v-model="configuration.Info.PeerHistoricalEndpointTracking" :id="configuration.Name + '_historicalEndpoint_tracking'">
						<label class="form-check-label" :for="configuration.Name + '_historicalEndpoint_tracking'">
							{{ configuration.Info.PeerHistoricalEndpointTracking ? 'On':'Off'}}
						</label>
					</div>
					<hr />
					<div class="d-flex align-items-start align-items-md-center flex-column flex-md-row gap-2">
						<div>
							<h6 class="placeholder animate__animated animate__flash animate__infinite animate__slower w-100 mb-0" v-if="!sizeDataLoaded"></h6>
							<h6 v-else class="mb-0">
								{{ sizes.HistoricalTrackingTableSize }} <span class="text-muted fw-normal"><LocaleText t="Records"></LocaleText></span>
							</h6>
						</div>
						<div class="ms-md-auto d-flex gap-2" v-if="confirmDelete !== 'HistoricalTrackingTable'">
							<button
								@click="download('HistoricalTrackingTable')"
								:class="{disabled: downloading === 'HistoricalTrackingTable'}"
								class="btn btn-sm bg-primary-subtle text-primary-emphasis rounded-3">
								<i class="bi bi-download me-2 "></i>
								<LocaleText :t="downloading === 'HistoricalTrackingTable' ? 'Downloading...':'Download'"></LocaleText>
							</button>
							<button class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3" @click="confirmDelete = 'HistoricalTrackingTable'">
								<i class="bi bi-trash me-2 "></i>Delete
							</button>
						</div>
						<div class="ms-md-auto d-flex gap-2 align-items-center" v-else-if="confirmDelete === 'HistoricalTrackingTable'">
							<small>
								<LocaleText t="Are you sure to delete?"></LocaleText>
							</small>
							<button class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3"
									:class="{disabled: deleting}"
									@click="deleteRecord('HistoricalTrackingTable')">
								<i class="bi bi-check me-2 "></i>Yes
							</button>
							<button
								:class="{disabled: deleting}"
								class="btn btn-sm bg-secondary-subtle text-secondary-emphasis rounded-3" @click="confirmDelete = ''">
								<i class="bi bi-x me-2 "></i>No
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>