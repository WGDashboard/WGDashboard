<script setup lang="ts" async>
import {useRoute, useRouter} from "vue-router";
import { fetchGet, fetchPost } from "@/utilities/fetch.js"


import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"

import {computed, reactive, ref, watch, onBeforeUnmount} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import ClientAssignedPeers from "@/components/clientComponents/clientAssignedPeers.vue";
import ClientResetPassword from "@/components/clientComponents/clientResetPassword.vue";
import ClientDelete from "@/components/clientComponents/clientDelete.vue";
const assignmentStore = DashboardClientAssignmentStore()
const dashboardConfigurationStore = DashboardConfigurationStore()

const route = useRoute()
const router = useRouter()
const client = computed(() => {
	return assignmentStore.getClientById(route.params.id)
})
const clientAssignedPeers = ref({})
const realtimeUsage = ref({sent_bps: 0, recv_bps: 0, updated_at: null})
const rateUnit = ref(window.localStorage.getItem('wgdashboard_rate_unit') || 'Mbps')
const getAssignedPeers = async () => {
	await fetchGet('/api/clients/assignedPeers', {
		ClientID: client.value.ClientID
	}, (res) => {
		clientAssignedPeers.value = res.data;
	})
}
const getRealtimeUsage = async () => {
	await fetchGet('/api/clients/realtimeUsage', {
		ClientID: client.value.ClientID
	}, (res) => {
		realtimeUsage.value = res.data || {sent_bps: 0, recv_bps: 0, updated_at: null}
	})
}
const emits = defineEmits(['deleteSuccess'])

const clientProfile = reactive({
	Name: undefined
})
const formatRate = (bps) => {
	const v = Number(bps || 0)
	if (rateUnit.value === 'MB/s'){
		return `${(v / 1000000).toFixed(2)} MB/s`
	}
	return `${(v * 8 / 1000000).toFixed(2)} Mbps`
}
const updateRateUnit = (e) => {
	rateUnit.value = e.target.value
	window.localStorage.setItem('wgdashboard_rate_unit', rateUnit.value)
}

if (client.value){
	watch(() => client.value.ClientID, async () => {
		clientProfile.Name = client.value.Name;
		await getAssignedPeers()
		await getRealtimeUsage()
		setRealtimeInterval()
	})
	await getAssignedPeers()
	await getRealtimeUsage()
	clientProfile.Name = client.value.Name
	setRealtimeInterval()
}else{
	router.push('/clients')
	dashboardConfigurationStore.newMessage("WGDashboard", "Client does not exist", "danger")
}



const updatingProfile = ref(false)
const updateProfile = async () => {
	updatingProfile.value = true
	await fetchPost("/api/clients/updateProfileName", {
		ClientID: client.value.ClientID,
		Name: clientProfile.Name
	}, (res) => {
		if (res.status){
			client.value.Name = clientProfile.Name;
			dashboardConfigurationStore.newMessage("Server", "Client name update success", "success")
		}else{
			clientProfile.Name = client.value.Name;
			dashboardConfigurationStore.newMessage("Server", "Client name update failed", "danger")
		}
		updatingProfile.value = false
	})
}
const deleteSuccess = async () => {
	await router.push('/clients')
	await assignmentStore.getClients()
}

const realtimeInterval = ref(undefined)
const setRealtimeInterval = () => {
	clearInterval(realtimeInterval.value)
	realtimeInterval.value = setInterval(async () => {
		await getRealtimeUsage()
	}, 5000)
}
onBeforeUnmount(() => {
	clearInterval(realtimeInterval.value)
	realtimeInterval.value = undefined
})

</script>

<template>
	<div class="text-body d-flex flex-column overflow-y-scroll h-100" v-if="client" :key="client.ClientID">
		<div class="p-4 border-bottom bg-body-tertiary z-0">
			<div class="mb-3 backLink">
				<RouterLink to="/clients" class="text-body text-decoration-none">
					<i class="bi bi-arrow-left me-2"></i>
					Back</RouterLink>
			</div>
			<small class="text-muted">
				<LocaleText t="Email"></LocaleText>
			</small>
			<h1>
				{{ client.Email }}
			</h1>
			<div class="d-flex flex-column gap-2">
				<div class="d-flex align-items-center">
					<small class="text-muted">
						<LocaleText t="Client ID"></LocaleText>
					</small>
					<small class="ms-auto">
						<samp>{{ client.ClientID }}</samp>
					</small>
				</div>
				<div class="d-flex align-items-center gap-2">
					<small class="text-muted">
						<LocaleText t="Client Name"></LocaleText>
					</small>
					<input class="form-control form-control-sm rounded-3 ms-auto"
						   style="width: 300px"
						   type="text" v-model="clientProfile.Name">
					<button
						@click="updateProfile()"
						aria-label="Save Client Name"
						class="btn btn-sm rounded-3 bg-success-subtle border-success-subtle text-success-emphasis">
						<i class="bi bi-save-fill"></i>
					</button>
				</div>
			</div>
		</div>
		<div class="p-3 border-bottom">
			<div class="d-flex justify-content-end align-items-center gap-2 mb-2">
				<small class="text-muted"><LocaleText t="Realtime Units"></LocaleText></small>
				<select class="form-select form-select-sm w-auto" @change="updateRateUnit">
					<option value="Mbps" :selected="rateUnit === 'Mbps'">Mbps</option>
					<option value="MB/s" :selected="rateUnit === 'MB/s'">MB/s</option>
				</select>
			</div>
			<div class="row g-3">
				<div class="col-lg-3">
					<div class="card rounded-3 h-100">
						<div class="card-body">
							<small class="text-muted">
								<LocaleText t="Realtime Speed"></LocaleText>
							</small>
							<div class="h5 mb-1">
								{{ formatRate(realtimeUsage.recv_bps) }} ↓
							</div>
							<div class="h6 text-muted mb-0">
								{{ formatRate(realtimeUsage.sent_bps) }} ↑
							</div>
							<div class="small text-muted mt-1">
								<LocaleText t="Updated"></LocaleText>: {{ realtimeUsage.updated_at || '—' }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div style="flex: 1 0 0; overflow-y: scroll;">
			<ClientAssignedPeers
				@refresh="getAssignedPeers()"
				:clientAssignedPeers="clientAssignedPeers"
				:client="client"></ClientAssignedPeers>
<!--			<ClientResetPassword-->
<!--				:client="client" v-if="client.ClientGroup === 'Local'"></ClientResetPassword>-->
			<ClientDelete
				@deleteSuccess="deleteSuccess()"
				:client="client"></ClientDelete>
		</div>
	</div>
	<div v-else class="d-flex w-100 h-100 text-muted">
		<div class="m-auto text-center">
			<h1>
				<i class="bi bi-person-x"></i>
			</h1>
			<p>
				<LocaleText t="Client does not exist"></LocaleText>
			</p>
		</div>
	</div>
</template>

<style scoped>
@media screen and (min-width: 576px) {
	.backLink{
		display: none;
	}
}
</style>
