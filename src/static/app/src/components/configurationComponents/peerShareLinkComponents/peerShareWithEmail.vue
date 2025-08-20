<script setup async>
import LocaleText from "@/components/text/localeText.vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {reactive, ref, watch} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import PeerShareWithEmailBodyPreview
	from "@/components/configurationComponents/peerShareLinkComponents/peerShareWithEmailBodyPreview.vue";
import {GetLocale} from "@/utilities/locale.js";
const props = defineProps(['dataCopy', 'selectedPeer'])
const emailIsReady = ref(false)
await fetchGet("/api/email/ready", {}, (res) => {
	emailIsReady.value = res.status
})
const store = DashboardConfigurationStore()
const email = reactive({
	Receiver: "",
	Body: store.Configuration.Email.email_template,
	Subject: "",
	IncludeAttachment: false,
	ConfigurationName: props.selectedPeer.configuration.Name,
	Peer: props.selectedPeer.id
})

const livePreview = ref(false)

const sending = ref(false)

const sendEmail = async () => {
	sending.value = true;
	await fetchPost("/api/email/send", email, (res) => {
		if (res.status){
			store.newMessage("Server", "Email sent successfully!", "success")
		}else{
			store.newMessage("Server", `Email sent failed! Reason: ${res.message}`, "danger")
		}
		sending.value = false
	})
}


const emits = defineEmits(['fullscreen', 'hide'])
watch(livePreview, () => {
	emits('fullscreen', livePreview.value)
})

</script>

<template>
	<div v-if="emailIsReady">
		<div class="d-flex mb-3 align-items-center">
			<a role="button" class="d-flex text-decoration-none text-body text-muted" @click="emits('hide')">
				<i class="bi bi-chevron-left me-2"></i> Back
			</a>
			<h6 class="mb-0 ms-auto">
				<LocaleText t="Share with Email"></LocaleText>
			</h6>
		</div>
		<form class="d-flex gap-3 flex-column"
			@submit="(e) => {e.preventDefault(); sendEmail()}"
		>
			<div>
				<div class="position-relative" >
					<i class="bi bi-person-circle" style="position: absolute; top: 0.4rem; left: 0.75rem;"></i>
					<input type="email" class="form-control rounded-top-3 rounded-bottom-0"
					       style="padding-left: calc( 0.75rem + 24px )"
					       v-model="email.Receiver"
					       :disabled="sending"
					       :placeholder="GetLocale('Who are you sending to?')"
					       required
					       id="email_receiver" aria-describedby="emailHelp">
				</div>
				<div class="position-relative">
					<i class="bi bi-hash" style="position: absolute; top: 0.4rem; left: 0.75rem;"></i>
					<input type="text" class="form-control rounded-0 border-top-0 border-bottom-0"
					       style="padding-left: calc( 0.75rem + 24px )"
					       :placeholder="GetLocale('What\'s the subject?')"
					       :disabled="sending"
					       v-model="email.Subject"
					       id="email_subject" aria-describedby="emailHelp">
				</div>
				<div class="row g-0">
					<div :class="[livePreview ? 'col-6' : 'col-12']">
						<textarea class="form-control rounded-top-0 rounded-bottom-0 font-monospace border-bottom-0"
						          v-model="email.Body"
						          :disabled="sending"
						          :placeholder="GetLocale('What\'s the body?')"
						          style="height: 400px; max-height: 400px;"></textarea>
					</div>
					<div class="col-6" v-if="livePreview">
						<PeerShareWithEmailBodyPreview
							:body="email.Body"
							:selectedPeer="selectedPeer"
						>
						</PeerShareWithEmailBodyPreview>
					</div>
				</div>
				
				<div class="card border-top-0 rounded-top-0 rounded-bottom-3 bg-body-tertiary" 
				     style="border: var(--bs-border-width) solid var(--bs-border-color)">
					<div class="card-body d-flex flex-column gap-2">
						<div class="form-check form-switch ms-auto">
							<input class="form-check-input" type="checkbox"
							       v-model="livePreview"
							       role="switch" id="livePreview">
							<label class="form-check-label" for="livePreview">
								<LocaleText t="Live Preview"></LocaleText>
							</label>
						</div>
						
					</div>
				</div>
				
			</div>
			<div class="form-check form-switch">
				<input class="form-check-input" type="checkbox" 
				       v-model="email.IncludeAttachment"
				       role="switch" id="includeAttachment">
				<label class="form-check-label" for="includeAttachment">
					<LocaleText t="Include configuration file as an attachment"></LocaleText>
				</label>
			</div>
			<button
				:disabled="sending"
				class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3">
				<span v-if="!sending">
					<i class="bi bi-send me-2"></i><LocaleText t="Send"></LocaleText>
				</span>
				<span v-else>
					<span class="spinner-border spinner-border-sm me-2"></span>
					<LocaleText t="Sending..."></LocaleText>
				</span>
			</button>
		</form>
	</div>
	<div v-else>
		<small>
			<LocaleText t="SMTP is not configured, please navigate to "></LocaleText>
			<RouterLink to="/settings">
				<LocaleText t="Settings"></LocaleText>
			</RouterLink>
			<LocaleText t=" to finish setup"></LocaleText>
		</small>
	</div>
</template>

<style scoped>
textarea:focus, input:focus{
	box-shadow: none;
	border-color: var(--bs-border-color) !important;
}

textarea{
	padding: var(--bs-card-spacer-y) var(--bs-card-spacer-x);
}
</style>