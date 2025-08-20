<script setup lang="ts" async>
import {useRoute, useRouter} from "vue-router";
import { fetchGet, fetchPost } from "@/utilities/fetch.js"


import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"

import {computed, reactive, ref, watch} from "vue";
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
const getAssignedPeers = async () => {
	await fetchGet('/api/clients/assignedPeers', {
		ClientID: client.value.ClientID
	}, (res) => {
		clientAssignedPeers.value = res.data;
	})
}
const emits = defineEmits(['deleteSuccess'])

const clientProfile = reactive({
	Name: undefined
})

if (client.value){
	watch(() => client.value.ClientID, async () => {
		clientProfile.Name = client.value.Name;
		await getAssignedPeers()
	})
	await getAssignedPeers()
	clientProfile.Name = client.value.Name
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
		<div style="flex: 1 0 0; overflow-y: scroll;">
			<ClientAssignedPeers
				@refresh="getAssignedPeers()"
				:clientAssignedPeers="clientAssignedPeers"
				:client="client"></ClientAssignedPeers>
			<ClientResetPassword
				:client="client" v-if="client.ClientGroup === 'Local'"></ClientResetPassword>
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