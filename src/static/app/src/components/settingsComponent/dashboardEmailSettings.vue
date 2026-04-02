<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {onMounted, ref} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
const store = DashboardConfigurationStore()

onMounted(() => {
	checkEmailReady()
	document.querySelectorAll("#emailAccount input, #emailAccount select, #email_template").forEach(x => {
		x.addEventListener("change", async () => {
			let id = x.attributes.getNamedItem('id').value;
			await fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Email",
				key: id,
				value: store.Configuration.Email[id]
			}, (res) => {
				if (res.status){
					x.classList.remove('is-invalid')
					x.classList.add('is-valid')
				}else{
					x.classList.remove('is-valid')
					x.classList.add('is-invalid')
				}
				checkEmailReady()
			})
		})
	})
})

const emailIsReady = ref(false)
const testEmailReceiver = ref("")
const testing = ref(false)

const checkEmailReady = async () => {
	await fetchGet("/api/email/ready", {}, (res) => {
		emailIsReady.value = res.status
	})
}

const sendTestEmail = async () => {
	testing.value = true
	await fetchPost("/api/email/send", {
		Receiver: testEmailReceiver.value,
		Subject: "WGDashboard Testing Email",
		Body: "Test 1, 2, 3! Hello World :)"
	}, (res) => {
		if (res.status){
			store.newMessage("Server", "Test email sent successfully!", "success")
		}else{
			store.newMessage("Server", `Test email sent failed! Reason: ${res.message}`, "danger")
		}
		testing.value = false
	})
}

</script>

<template>
	<div class="card">
		<div class="card-header">
			<h6 class="my-2 d-flex">
				<i class="bi bi-envelope-fill me-2"></i>
				<LocaleText t="Email Account"></LocaleText>
				<span class="text-success ms-auto" v-if="emailIsReady">
					<i class="bi bi-check-circle-fill me-2"></i>
					<LocaleText t="Ready"></LocaleText>
				</span>
			</h6>
		</div>
		<div class="card-body d-flex flex-column gap-3">
			<form @submit="(e) => e.preventDefault(e)" id="emailAccount">
				<div class="row gx-2 gy-2">
					<div class="col-12">
						<div class="form-check mb-2 form-switch">
							<input class="form-check-input" type="checkbox" role="switch"
								   v-model="store.Configuration.Email.authentication_required"
								   id="authentication_required">
							<label class="form-check-label" for="authentication_required">
								<LocaleText t="Require SMTP Authentication"></LocaleText>
							</label>
						</div>
					</div>
					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="server" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Server"></LocaleText>
								</small></strong>
							</label>
							<input id="server" 
							       v-model="store.Configuration.Email.server"
							       type="text" class="form-control rounded-3">
						</div>
					</div>
					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="port" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Port"></LocaleText>
								</small></strong>
							</label>
							<input id="port"
							       v-model="store.Configuration.Email.port"
							       type="text" class="form-control rounded-3">
						</div>
					</div>
					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="encryption" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Encryption"></LocaleText>
								</small></strong>
							</label>
							<select class="form-select rounded-3"
							        v-model="store.Configuration.Email.encryption"
							        id="encryption">
								<option value="STARTTLS">
									STARTTLS
								</option>
								<option value="NOTLS">
									<LocaleText t="No Encryption"></LocaleText>
								</option>
							</select>
						</div>
					</div>
					<div class="col-12 col-lg-4" v-if="store.Configuration.Email.authentication_required">
						<div class="form-group">
							<label for="username" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Username"></LocaleText>
								</small></strong>
							</label>
							<input id="username"
							       v-model="store.Configuration.Email.username"
							       type="text" class="form-control rounded-3">
						</div>
					</div>
					<div class="col-12 col-lg-4" v-if="store.Configuration.Email.authentication_required">
						<div class="form-group">
							<label for="email_password" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Password"></LocaleText>
								</small></strong>
							</label>
							<input id="email_password"
							       v-model="store.Configuration.Email.email_password"
							       type="password" class="form-control rounded-3">
						</div>
					</div>

					<div class="col-12 col-lg-4">
						<div class="form-group">
							<label for="send_from" class="text-muted mb-1">
								<strong><small>
									<LocaleText t="Send From"></LocaleText>
								</small></strong>
							</label>
							<input id="send_from"
							       v-model="store.Configuration.Email.send_from"
							       type="text" class="form-control rounded-3">
						</div>
					</div>

				</div>
			</form>
			<hr v-if="emailIsReady">
			<div v-if="emailIsReady">
				<label class="text-muted mb-1" for="test_email">
					<small class="fw-bold">
						<LocaleText t="Send Test Email"></LocaleText>
					</small>
				</label>
				<form
					@submit="(e) => {e.preventDefault(); sendTestEmail()}"
					class="input-group">
					<input type="email" class="form-control rounded-start-3"
					       id="test_email"
					       placeholder="john@example.com"
					       v-model="testEmailReceiver"
					       :disabled="testing">
					<button class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-end-3"
					        type="submit" value="Submit"
					        :disabled="testEmailReceiver.length === 0 || testing"
					        id="button-addon2">
						<i class="bi bi-send me-2" v-if="!testing"></i>
						<span class="spinner-border spinner-border-sm me-2" v-else>
					</span>
						<LocaleText :t="!testing ? 'Send':'Sending...'"></LocaleText>
					</button>
				</form>
			</div>
			<hr>
			<div>
				<label class="text-muted mb-1" for="email_template">
					<small class="fw-bold">
						<LocaleText t="Email Body Template"></LocaleText>
					</small>
				</label>
				<textarea class="form-control rounded-3 font-monospace"
				          v-model="store.Configuration.Email.email_template"
				          id="email_template"
				          style="min-height: 400px"></textarea>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>