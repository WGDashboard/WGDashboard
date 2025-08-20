<script setup lang="ts">
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
import LocaleText from "@/components/text/localeText.vue";
import {computed, ref} from "vue";
const assignmentStore = DashboardClientAssignmentStore()
import {GetLocale} from "@/utilities/locale.js";
import ClientGroup from "@/components/clientComponents/clientGroup.vue";
import { fetchGet } from "@/utilities/fetch.js"
import {useRoute} from "vue-router";
import ClientSettings from "@/components/clientComponents/clientSettings.vue";

await assignmentStore.getClients();
assignmentStore.getAllConfigurationsPeers();

const searchString = ref("")
const route = useRoute()
const settings = ref(false)
const oidc = computed(() => {
	return Object.fromEntries(
		Object.entries(assignmentStore.clients).filter(
			([key, _])=>Object.keys(assignmentStore.clients).filter(x => x !== 'Local').includes(key)
		)
	)
})

const deleteSuccess = async () => {
	await assignmentStore.getClients();
}
</script>

<template>
	<div class="text-body w-100 h-100 pb-2 position-relative">

		<div class="w-100 h-100 card rounded-3">
			<Transition name="zoom">
				<ClientSettings v-if="settings" @close="settings = false"></ClientSettings>
			</Transition>
			<div class="border-bottom z-0">
				<div class="d-flex text-body align-items-center sticky-top p-3 bg-body-tertiary rounded-top-3" style="border-top-right-radius: 0 !important;">
					<label for="searchClient"><i class="bi bi-search me-2"></i></label>
					<input
						v-model="searchString"
						id="searchClient"
						class="form-control rounded-3 form-control-sm"
						:placeholder="GetLocale('Search Clients...')"
						type="email" style="width: auto;">
					<button class="btn btn-body ms-auto bg-body-secondary rounded-3 btn-sm" @click="settings = !settings">
						<i class="bi bi-gear-fill me-2"></i>
						<LocaleText t="Settings"></LocaleText>
					</button>
				</div>
			</div>
			<div class="row h-100 g-0">
				<div
					:class="{'hide': route.params.id}"
					class="col-sm-4 border-end d-flex flex-column clientListContainer">
					<div class="d-flex flex-column overflow-y-scroll" style="flex: 1 0 0">
						<ClientGroup :searchString="searchString"
									 v-if="Object.keys(assignmentStore.clients).includes('Local')"
									 :clients="assignmentStore.clients.Local" groupName="Local"></ClientGroup>
						<ClientGroup v-for="(clients, groupName) in oidc"
						             :searchString="searchString"
						             :clients="clients" :groupName="groupName"></ClientGroup>
					</div>
				</div>
				<div
					:class="{'hide': !route.params.id}"
					class="col-sm-8 clientViewerContainer">
					<RouterView></RouterView>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
@media screen and (max-width: 576px){
	.clientListContainer.hide, .clientViewerContainer.hide{
		display: none !important;
	}

	.clientListContainer{
		border-right: none !important;
		animation: blurIn 0.2s ease-in-out forwards;
	}

	.clientViewerContainer{
		animation: blurIn 0.2s ease-in-out forwards;
	}
}

@keyframes blurIn {
	from{
		filter: blur(8px);
	}
	to{
		filter: blur(0px);
	}
}
</style>