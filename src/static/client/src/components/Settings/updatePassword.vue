<script setup>
import {reactive, ref} from "vue";
import {axiosPost} from "@/utilities/request.js";
import {clientStore} from "@/stores/clientStore.js";

const Password = reactive({
	CurrentPassword: "",
	NewPassword: "",
	ConfirmNewPassword: ""
})

const ResetPasswordFields = () => {
	Password.CurrentPassword = ""
	Password.NewPassword = ""
	Password.ConfirmNewPassword = ""
}
const store = clientStore()
const UpdatePassword = async (e) => {
	e.preventDefault();
	document.querySelectorAll("#updatePasswordForm input").forEach(x => x.blur())
	const data = await axiosPost('/api/settings/updatePassword', Password)
	if(data){
		if (!data.status){
			formInvalid.value = true;
			formInvalidMessage.value = data.message;
		}else{
			formInvalid.value = false
			store.newNotification("Password updated!", "success")
			ResetPasswordFields()
		}
	}else{
		formInvalid.value = true;
		formInvalidMessage.value = "Error occurred"
	}
}

const showPassword = ref(false)
const formInvalid = ref(false)
const formInvalidMessage = ref("")
</script>

<template>
	<form @submit="(e) => UpdatePassword(e)"
	      id="updatePasswordForm"
	      @reset="ResetPasswordFields()" class="p-3">
		<div class="d-flex align-items-start">
			<h5>
				Update Password
			</h5>
			<a role="button"
			   @click="showPassword = !showPassword"
			   class="text-muted ms-auto text-decoration-none">
				<small>
					<i
						:class="[showPassword ? 'bi-eye-slash-fill':'bi-eye-fill']"
						class="bi me-2"></i>{{ showPassword ? 'Hide':'Show'}} Password
				</small>
			</a>
		</div>
		<div class="alert alert-danger rounded-3 mt-3" v-if="formInvalid">
			{{ formInvalidMessage }}
		</div>
		<div class="row g-2 mb-3">
			<div class="col-sm-12">
				<label
					class="text-muted form-label" for="CurrentPassword">
					<small>Current Password</small>
				</label>
				<input class="form-control rounded-3" :class="{'is-invalid': formInvalid}" required
				       :type="showPassword ? 'text':'password'" autocomplete="current-password" id="CurrentPassword" v-model="Password.CurrentPassword">
			</div>
			<div class="col-sm-6">
				<label class="text-muted form-label" for="NewPassword">
					<small>New Password</small>
				</label>
				<input class="form-control rounded-3"
				       required
				       :class="{'is-invalid': formInvalid}"
				       :type="showPassword ? 'text':'password'"
				       id="NewPassword" autocomplete="new-password" v-model="Password.NewPassword">
			</div>
			<div class="col-sm-6">
				<label class="text-muted form-label" for="ConfirmNewPassword">
					<small>Confirm New Password</small>
				</label>
				<input class="form-control rounded-3"
				       required
				       :class="{'is-invalid': formInvalid}"
				       :type="showPassword ? 'text':'password'"
				       id="ConfirmNewPassword" autocomplete="new-password" v-model="Password.ConfirmNewPassword">
			</div>
		</div>
		<div class="d-flex gap-2">
			<button class="btn btn-sm btn-secondary rounded-3 ms-auto" type="reset">Clear</button>
			<button class="btn btn-sm btn-danger rounded-3" type="submit">Update</button>
		</div>
	</form>
</template>

<style scoped>

</style>