<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import { fetchGet, fetchPost } from "@/utilities/fetch.js"
import {ref} from "vue";
import {DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"
import {useRouter} from "vue-router";
const props = defineProps(['client'])


const alert = ref(false)
const alertStatus = ref(false)
const alertMessage = ref(false)
const resetting = ref(false)
const store = DashboardConfigurationStore();
const router = useRouter()

const getUrl = (token) => {
	const crossServer = store.getActiveCrossServer();
	if(crossServer){
		return new URL('/client/#/reset_password?token=' + token, crossServer.host).href
	}
	return new URL('/client/#/reset_password?token=' + token, window.location.href).href
}

const sendResetLink = async () => {
	resetting.value = true
	let smtpReady = false;
	let token = undefined;
	await fetchPost('/api/clients/generatePasswordResetLink', {
		ClientID: props.client.ClientID
	},async (res) => {
		if (res.status){
			token = res.data
			alertStatus.value = true
			await fetchGet('/api/email/ready', {}, (res) => {
				smtpReady = res.status
			});
			if (smtpReady){
				let body = {
					"Receiver": props.client.Email,
					"Subject": "[WGDashboard | Client] Reset Password",
					"Body":
						`Hi${props.client.Name ? ' ' + props.client.Name: ''},\n\nWe received a request to reset the password for your account. You can reset your password by visiting the link below:\n\n${getUrl(token)}\n\nThis link will expire in 30 minutes for your security. If you didn’t request a password reset, you can safely ignore this email—your current password will remain unchanged.\n\nIf you need help, feel free to contact support.\n\nBest regards,\nWGDashboard`
				}
				await fetchPost('/api/email/send', body, (res) => {
					if (res.status){
						alertMessage.value = `Send email success.`
						alert.value = true;
					}else{
						alertMessage.value = `Send email failed.`
						alertStatus.value = false;
						alert.value = true;
					}
				});
			}else{
				alertMessage.value = `Please share this URL to your client to reset the password: ${getUrl(token)}`
				alert.value = true;

			}
		}else{
			alertStatus.value = false
			alertMessage.value = res.message
			alert.value = true
		}
	})
	resetting.value = false;
}

</script>

<template>
<div class="p-3 d-flex gap-3 flex-column border-bottom">
	<div class="d-flex align-items-center">
		<h6 class="mb-0">
			<LocaleText t="Reset Password"></LocaleText>
		</h6>
		<button class="btn btn-sm bg-primary-subtle text-primary-emphasis rounded-3 ms-auto"
			@click="sendResetLink()"
				:class="{disabled: resetting}"
		>
			<i class="bi bi-send me-2"></i>
			<LocaleText t="Send Password Reset Link" v-if="!resetting"></LocaleText>
			<LocaleText t="Sending..." v-else></LocaleText>
		</button>
	</div>
	<div class="alert rounded-3 mb-0"
		 :class="[alertStatus ? 'alert-success' : 'alert-danger']"
		 v-if="alert">
		{{ alertMessage }}
	</div>
</div>
</template>

<style scoped>

</style>