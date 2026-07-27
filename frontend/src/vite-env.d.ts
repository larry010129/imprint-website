/// <reference types="vite/client" />

declare module "@heroui/styles/css"

interface GoogleCredentialResponse {
  credential: string
}

interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (config: {
          client_id: string
          callback: (response: GoogleCredentialResponse) => void
          auto_select?: boolean
        }) => void
        renderButton: (
          parent: HTMLElement,
          options: {
            theme?: string
            size?: string
            width?: number
            locale?: string
            text?: string
          },
        ) => void
      }
    }
  }
}
