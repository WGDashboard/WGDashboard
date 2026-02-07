<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {onMounted, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import QRCode from "qrcode";
import {useRoute} from "vue-router";
const emit = defineEmits(['close'])
const props = defineProps({
	selectedPeer: Object
})
const store = DashboardConfigurationStore()
const copied = ref(false)
const configurationFile = ref("")
const loading = ref(true)
const error = ref({
	error: false,
	message: undefined
})

onMounted(() => {
	const route = useRoute();
	fetchGet("/api/downloadPeer/"+route.params.id, {
		id: props.selectedPeer.id
	}, (res) => {
		if (res.status){
			configurationFile.value = res.data.file
			loading.value = false;
		}else{
			this.dashboardStore.newMessage("Server", res.message, "danger")
		}
	})
})

const copy = async () => {
	if (navigator.clipboard && navigator.clipboard.writeText){
		navigator.clipboard.writeText(configurationFile.value).then(() => {
			copied.value = true;
			setTimeout(() => {
				copied.value = false;
			}, 3000)
		}).catch(() => {
			store.newMessage("WGDashboard","Failed to copy", "danger");
		})
	}else{
		const ele = document.querySelector("#peerConfigurationFile");
		ele.select();
		const successful = document.execCommand("copy");
		if (successful) {
			copied.value = true;
			setTimeout(() => {
				copied.value = false;
			}, 3000)
		} else {
			store.newMessage("WGDashboard","Failed to copy", "danger");
		}
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal justify-content-center">
				<div class="card rounded-3 shadow w-100">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h4 class="mb-0">
							<LocaleText t="Peer Configuration File"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" 
						        @click="emit('close')" aria-label="Close"></button>
					</div>
					<div class="card-body p-4 d-flex flex-column gap-3">
						<div style="height: 300px" class="d-flex">
							<textarea
								style="height: 300px"
								class="form-control w-100 rounded-3 animate__fadeIn animate__faster animate__animated"
								id="peerConfigurationFile"
								:class="{'d-none': loading}"
								:value="configurationFile"></textarea>
							<div class="spinner-border m-auto" role="status" v-if="loading">
								<span class="visually-hidden">Loading...</span>
							</div>
						</div>
						<div class="d-flex">
							<button
								@click="copy()"
								:disabled="copied || loading"
								class="ms-auto btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 position-relative">
								<Transition name="slide-up" mode="out-in">
									<span v-if="!copied" class="d-block">
										<i class="bi bi-clipboard-fill"></i>
									</span>
									<span v-else class="d-block" id="check">
										<i class="bi bi-check-circle-fill"></i>
									</span>
								</Transition>
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
	transition: all 0.2s cubic-bezier(0.42, 0, 0.22, 1);
}

.slide-up-enter-from, .slide-up-leave-to {
	opacity: 0;
	transform: scale(0.9);
}

@keyframes spin {
	from{
		transform: rotate(0deg);
	}
	to{
		transform: rotate(360deg);
	}
}

#check{
	animation: cubic-bezier(0.42, 0, 0.22, 1.3) 0.7s spin;
}
</style>