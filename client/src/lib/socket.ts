import { io, Socket } from 'socket.io-client'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:5050`

let teamSocket: Socket | undefined
let globalSocket: Socket | undefined

export function getTeamSocket(): Socket {
  if (!teamSocket) {
    teamSocket = io(`${API_BASE_URL}/team`, {
      withCredentials: true,
      transports: ['polling', 'websocket'],
    })
  }
  return teamSocket
}

export function getGlobalSocket(): Socket {
  if (!globalSocket) {
    globalSocket = io(`${API_BASE_URL}/global`, {
      withCredentials: true,
      transports: ['polling', 'websocket'],
    })
  }
  return globalSocket
}
