package ca.kladriva.musicrefs.data.model

import ca.kladriva.musicrefs.domain.game.Hints
import ca.kladriva.musicrefs.domain.game.Quote
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class HintsDto(
    val year: String = "",
    val genre: String = "",
    val album: String = "",
    val initials: String = "",
) {
    fun toDomain() = Hints(year = year, genre = genre, album = album, initials = initials)
}

@Serializable
data class QuoteDto(
    val id: Int,
    val quote: String,
    val artist: String,
    val title: String,
    val hints: HintsDto = HintsDto(),
    @SerialName("category_ids") val categoryIds: List<Int> = emptyList(),
) {
    fun toDomain() = Quote(
        id = id,
        quote = quote,
        artist = artist,
        title = title,
        hints = hints.toDomain(),
        categoryIds = categoryIds,
    )
}

@Serializable
data class CategoryDto(
    val id: Int,
    val slug: String,
    val name: String,
    val description: String = "",
    @SerialName("quote_count") val quoteCount: Int = 0,
)

@Serializable
data class PartyPlayerDto(
    val id: Int,
    val name: String,
    @SerialName("is_host") val isHost: Boolean = false,
    val score: Int = 0,
    val finished: Boolean = false,
    val progress: Int = 0,
    val total: Int = 0,
)

@Serializable
data class PartyMeDto(
    val id: Int,
    val name: String,
    @SerialName("is_host") val isHost: Boolean = false,
    val score: Int = 0,
    val finished: Boolean = false,
    val progress: Int = 0,
    val total: Int = 0,
    @SerialName("player_token") val playerToken: String? = null,
    @SerialName("host_token") val hostToken: String? = null,
)

@Serializable
data class PartyCategoryDto(
    val id: Int,
    val slug: String = "",
    val name: String = "",
    val description: String = "",
    @SerialName("quote_count") val quoteCount: Int = 0,
)

@Serializable
data class PartySnapshotDto(
    val id: Int,
    val code: String,
    val status: String,
    @SerialName("round_limit") val roundLimit: Int = 10,
    val mode: String = "classic",
    val category: PartyCategoryDto? = null,
    val players: List<PartyPlayerDto> = emptyList(),
    val me: PartyMeDto? = null,
    @SerialName("quote_count") val quoteCount: Int = 0,
)

@Serializable
data class PartyCreateRequest(
    @SerialName("category_id") val categoryId: Int,
    @SerialName("host_name") val hostName: String,
    @SerialName("round_limit") val roundLimit: Int = 10,
    val mode: String = "classic",
)

@Serializable
data class PartyJoinRequest(
    val code: String,
    @SerialName("player_name") val playerName: String,
)

@Serializable
data class PartyStartRequest(
    @SerialName("host_token") val hostToken: String,
)

@Serializable
data class PartyScoreRequest(
    @SerialName("player_token") val playerToken: String,
    val score: Int,
    val finished: Boolean = false,
    val progress: Int? = null,
)

@Serializable
data class ApiErrorBody(
    val detail: String? = null,
)

enum class GameMode(val apiValue: String, val label: String) {
    CLASSIC("classic", "Normal"),
    EASY("easy", "Facile"),
    ;

    companion object {
        fun fromApi(value: String?): GameMode =
            if (value == "easy") EASY else CLASSIC
    }
}
