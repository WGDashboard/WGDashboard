<script setup async>
import './assets/main.css'
import NotificationList from "@/components/Notification/notificationList.vue";
import {clientStore} from "@/stores/clientStore.js";

const store = clientStore()
fetch("/client/api/serverInformation")
	.then(res => res.json())
	.then(res => store.serverInformation = res.data)
</script>

<template>
	<div data-bs-theme="dark" class="text-body bg-body vw-100 vh-100 bg-body">
		<div class="d-flex vw-100 p-sm-4 overflow-y-scroll innerContainer d-flex flex-column">
			<div class="mx-auto my-sm-auto position-relative"
			     id="listContainer"
			     >
				<Suspense>
					<RouterView v-slot="{ Component }">
						<Transition name="app" type="transition" mode="out-in">
							<Component :is="Component"></Component>
						</Transition>
					</RouterView>
				</Suspense>
			</div>
			<div style="font-size: 0.8rem" class="text-center text-muted">
				<small>
					Background image by <a href="https://unsplash.com/photos/body-of-water-aExT3y92x5o">Fabrizio Conti</a>
				</small><br>
			</div>
		</div>
		<NotificationList></NotificationList>
	</div>
</template>

<style scoped>


#listContainer{
	width: 100%;
}

@media screen and (min-width: 992px) {
	#listContainer{
		width: 700px;
	}
}

.innerContainer{
	height: 100vh;
}

@supports(height: 100dvh) {
	.innerContainer { height: 100dvh; }
}

.bg-body[data-bs-theme="dark"]{
	background: linear-gradient(rgba(48, 48, 48, 0.5), rgba(0, 0, 0, 0.5)), url("/img/fabrizio-conti-aExT3y92x5o-unsplash.jpg") fixed;
	background-size: cover;
	background-position: top;
}
</style>
