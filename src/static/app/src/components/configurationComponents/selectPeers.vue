<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {computed, reactive, ref, useTemplateRef, watch} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const props = defineProps({
	configurationPeers: Array
})
const deleteConfirmation = ref(false)
const downloadConfirmation = ref(false)
const selectedPeers = ref([])
const selectPeersSearchInput = ref("")

const togglePeers = (id) => {
	if (selectedPeers.value.find(x => x === id)){
		selectedPeers.value = selectedPeers.value.filter(x => x !== id)
	}else{
		selectedPeers.value.push(id)
	}
}

const searchPeers = computed(() => {
	if (deleteConfirmation.value || downloadConfirmation.value){
		return props.configurationPeers.filter(x =>
			selectedPeers.value.find(y => y === x.id)
		)
	}
	if (selectPeersSearchInput.value.length > 0){
		return props.configurationPeers.filter(x => {
			return x.id.includes(selectPeersSearchInput.value) || x.name.includes(selectPeersSearchInput.value)
		})
	}
	return props.configurationPeers
})

watch(selectedPeers, () => {
	if (selectedPeers.value.length === 0){
		deleteConfirmation.value = false;
		downloadConfirmation.value = false;
	}
})

const route = useRoute()
const dashboardStore = DashboardConfigurationStore()
const emit = defineEmits(["refresh", "close"])
const submitting = ref(false)
const submitDelete = () => {
	submitting.value = true;
	fetchPost(`/api/deletePeers/${route.params.id}`, {
		peers: selectedPeers.value
	}, (res) => {
		dashboardStore.newMessage("Server", res.message, res.status ? "success":"danger")
		if (res.status){
			selectedPeers.value = []
			deleteConfirmation.value = false
		}
		emit("refresh")
		submitting.value = false;
	})
}

const downloaded = reactive({
	success: [],
	failed: []
})
const cardBody = useTemplateRef('card-body');
const el = useTemplateRef("sp")
const submitDownload = async () => {
	downloadConfirmation.value = true
	for (const x of selectedPeers.value) {
		cardBody.value.scrollTo({
			top: el.value.find(y => y.dataset.id === x).offsetTop - 20,
			behavior: 'smooth'
		})
		await fetchGet("/api/downloadPeer/"+route.params.id, {
			id: x
		}, (res) => {
			if (res.status){
				const blob = new Blob([res.data.file], { type: "text/plain" });
				const jsonObjectUrl = URL.createObjectURL(blob);
				const filename = `${res.data.fileName}.conf`;
				const anchorEl = document.createElement("a");
				anchorEl.href = jsonObjectUrl;
				anchorEl.download = filename;
				anchorEl.click();
				downloaded.success.push(x)
			}else{
				downloaded.failed.push(x)
			}
		})
	}
}
const clearDownload = () => {
	downloaded.success = []
	downloaded.failed = []
	downloadConfirmation.value = false;
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll" ref="selectPeersContainer">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 700px">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 p-4 flex-column pb-3">
						<div class="mb-2 w-100 d-flex">
							<h4 class="mb-0">
								<LocaleText t="Select Peers"></LocaleText>
							</h4>
							<button type="button" class="btn-close ms-auto"
							        @click="emit('close')" aria-label="Close"></button>
						</div>
						<div class="d-flex w-100 align-items-center gap-2">
							<div class="d-flex gap-3">
								<a role="button"
								   v-if="!downloadConfirmation && selectedPeers.length !== configurationPeers.map(x => x.id).length"
								   @click="selectedPeers = configurationPeers.map(x => x.id)"
								   class="text-decoration-none text-body">
									<small>
										<i class="bi bi-check-all me-2"></i>
										<LocaleText t="Select All"></LocaleText>
									</small>
								</a>
								<a role="button" class="text-decoration-none text-body"
								   @click="selectedPeers = []"
								   v-if="selectedPeers.length > 0 && !downloadConfirmation">
									<small>
										<i class="bi bi-x-circle-fill me-2"></i>
										<LocaleText t="Clear Selection"></LocaleText>
									</small>
								</a>
							</div>
							
							<label class="ms-auto" for="selectPeersSearchInput">
								<i class="bi bi-search"></i>	
							</label>
							<input class="form-control form-control-sm rounded-3"
							       v-model="selectPeersSearchInput"
							       id="selectPeersSearchInput"
							       style="width: 200px !important;" type="text">
						</div>
					</div>
					<div class="card-body px-4 flex-grow-1 d-flex gap-2 flex-column position-relative" 
					     ref="card-body"
					     style="overflow-y: scroll">
						<button type="button" class="btn w-100 peerBtn text-start rounded-3 d-flex align-items-center gap-3"
						        @click="togglePeers(p.id)"
						        :class="{active: selectedPeers.find(x => x === p.id)}"
						        :key="p.id"
						        :disabled="deleteConfirmation || downloadConfirmation"
						        ref="sp"
						        :data-id="p.id"
						        v-for="p in searchPeers">
							<span v-if="!downloadConfirmation">
									<i class="bi"
									   :class="[ selectedPeers.find(x => x === p.id) ? 'bi-check-circle-fill':'bi-circle']"
									></i>
								</span>
							<span class="d-flex flex-column">
								<small class="fw-bold">
									{{p.name ? p.name : "Untitled Peer"}}
								</small>
								<small class="text-muted">
									<samp>{{p.id}}</samp>
								</small>
							</span>
							<span v-if="downloadConfirmation" class="ms-auto">
								<span class="spinner-border spinner-border-sm" role="status"
								     v-if="!downloaded.success.find(x => x === p.id) && !downloaded.failed.find(x => x === p.id)">
								</span>
								<i class="bi"
								   v-else
								   :class="[downloaded.failed.find(x => x === p.id) ? 'bi-x-circle-fill':'bi-check-circle-fill']"
								></i>
							</span>
						</button>
					</div>
					<div class="card-footer px-4 py-3 gap-2 d-flex align-items-center">
						<template v-if="!deleteConfirmation && !downloadConfirmation">
							<button class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3"
							        :disabled="selectedPeers.length === 0 || submitting"
							        @click="submitDownload()"
							>
								<i class="bi bi-download"></i>
							</button>
							<span v-if="selectedPeers.length > 0" class="flex-grow-1 text-center">
								<i class="bi bi-check-circle-fill me-2"></i>
								<LocaleText :t="selectedPeers.length + ' Peer' + (selectedPeers.length > 1 ? 's':'')"></LocaleText>
							</span>
							<button class="btn bg-danger-subtle text-danger-emphasis border-danger-subtle ms-auto rounded-3"
							        @click="deleteConfirmation = true"
							        :disabled="selectedPeers.length === 0 || submitting"
							>
								<i class="bi bi-trash"></i>
							</button>
						</template>
						<template v-else-if="downloadConfirmation">
							<strong v-if="downloaded.failed.length + downloaded.success.length < selectedPeers.length" class="flex-grow-1 text-center">
								<LocaleText t="Downloading" /> <LocaleText :t="selectedPeers.length + ' Peer' + (selectedPeers.length > 1 ? 's':'')"></LocaleText>...
							</strong>
							<template v-else>
								<strong>
									<LocaleText t="Download Finished"></LocaleText>
								</strong>
								<button 
									@click="clearDownload()"
									class="btn bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle rounded-3 ms-auto">
									<LocaleText t="Done"></LocaleText>
								</button>
							</template>
						</template>
						<template v-else-if="deleteConfirmation">
							<button class="btn btn-danger rounded-3"
							        :disabled="selectedPeers.length === 0 || submitting"
							        @click="submitDelete()"
							>
								<LocaleText t="Yes"></LocaleText>
							</button>
							<strong v-if="selectedPeers.length > 0" class="flex-grow-1 text-center">
								<LocaleText t="Are you sure to delete"></LocaleText> <LocaleText :t="selectedPeers.length + ' Peer' + (selectedPeers.length > 1 ? 's':'')"></LocaleText>?
							</strong>
							<button class="btn bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle ms-auto rounded-3"
							        :disabled="selectedPeers.length === 0 || submitting"
							        @click="deleteConfirmation = false"
							>
								<LocaleText t="No"></LocaleText>
							</button>
						</template>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
	.card{
		height: 100%;
	}
	
	.dashboardModal{
		height: calc(100% - 1rem) !important;
	}
	
	@media screen and (min-height: 700px) {
		.card{
			height: 700px;
		}
	}
	
	.peerBtn{
		border: var(--bs-border-width) solid var(--bs-border-color);
	}
	.peerBtn.active{
		border: var(--bs-border-width) solid var(--bs-body-color);
	}
	
</style>