import axios from 'axios'
import { SetupInterceptors } from './SetupInterceptors'
import { API_BASE_URL } from '../endpoints'

const http = axios.create({
    baseURL: API_BASE_URL
})

SetupInterceptors(http)

export default http