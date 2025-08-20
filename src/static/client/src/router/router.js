import {createWebHashHistory, createRouter} from "vue-router";
import Index from "@/views/index.vue";
import SignIn from "@/views/signin.vue";
import SignUp from "@/views/signup.vue";
import axios from "axios";
import {axiosGet, requestURl} from "@/utilities/request.js";
import {clientStore} from "@/stores/clientStore.js";
import Settings from "@/views/settings.vue";

const router = createRouter({
	history: createWebHashHistory(),
	routes: [
		{
			path: '/',
			component: Index,
			meta: {
				auth: true
			},
			name: "Home"
		},
		{
			path: '/settings',
			component: Settings,
			meta: {
				auth: true
			},
			name: "Settings"
		},
		{
			path: '/signin',
			component: SignIn,
			name: "Sign In"
		},
		{
			path: '/signup',
			component: SignUp,
			name: "Sign Up"
		},
		{
			path: '/signout',
			name: "Sign Out"
		}
	]
})
router.beforeEach(async (to, from, next) => {
	const store = clientStore()
	if (to.path === '/signout'){
		await axios.get(requestURl('/api/signout')).then(() => {
			next('/signin')
		}).catch(() => {
			next('/signin')
		});
		store.newNotification("Sign in session ended, please sign in again", "warning")
	}else{
		if (to.meta.auth){
			const status = await axiosGet('/api/validateAuthentication')
			if (status){
				next()
			}else{
				store.newNotification("Sign in session ended, please sign in again", "warning")
				next('/signin')
			}
		}else{
			next()
		}
	}
})

router.afterEach((to, from, next) => {
	document.title = to.name + ' | WGDashboard Client'
})

export default router