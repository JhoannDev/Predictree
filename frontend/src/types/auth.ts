export interface Usuario {
  id_usuario: number;
  nombre_usuario: string;
  nombre_completo: string;
  rol: string;
}

export interface RespuestaLogin {
  access_token: string;
  token_type: string;
  usuario: Usuario;
}
