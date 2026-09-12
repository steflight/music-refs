package ca.kladriva.musicrefs.data.api

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import retrofit2.HttpException
import java.io.IOException

sealed class ApiResult<out T> {
    data class Ok<T>(val value: T) : ApiResult<T>()
    data class Err(val message: String) : ApiResult<Nothing>()
}

private val errorJson = Json { ignoreUnknownKeys = true }

fun Throwable.toUserMessage(): String = when (this) {
    is HttpException -> {
        val body = response()?.errorBody()?.string().orEmpty()
        parseDetail(body) ?: "Erreur réseau (${code()})"
    }
    is IOException -> "Connexion impossible. Vérifie le réseau."
    else -> message?.takeIf { it.isNotBlank() } ?: "Erreur inattendue"
}

private fun parseDetail(body: String): String? {
    if (body.isBlank()) return null
    return try {
        val el = errorJson.parseToJsonElement(body)
        val detail = el.jsonObject["detail"]
        when {
            detail == null -> null
            detail.jsonPrimitive.isString -> detail.jsonPrimitive.content
            else -> detail.toString()
        }
    } catch (_: Exception) {
        body.take(200)
    }
}

suspend fun <T> safeApi(block: suspend () -> T): ApiResult<T> = try {
    ApiResult.Ok(block())
} catch (t: Throwable) {
    ApiResult.Err(t.toUserMessage())
}
