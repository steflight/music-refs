package ca.kladriva.musicrefs.data.api

import ca.kladriva.musicrefs.data.model.CategoryDto
import ca.kladriva.musicrefs.data.model.PartyCreateRequest
import ca.kladriva.musicrefs.data.model.PartyJoinRequest
import ca.kladriva.musicrefs.data.model.PartyScoreRequest
import ca.kladriva.musicrefs.data.model.PartySnapshotDto
import ca.kladriva.musicrefs.data.model.PartyStartRequest
import ca.kladriva.musicrefs.data.model.QuoteDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface MusicRefsApi {
    @GET("/health")
    suspend fun health(): Map<String, String>

    @GET("/api/music-refs/categories")
    suspend fun categories(): List<CategoryDto>

    @GET("/api/music-refs/quotes")
    suspend fun quotes(@Query("category_id") categoryId: Int? = null): List<QuoteDto>

    @GET("/api/music-refs/random")
    suspend fun random(@Query("category_id") categoryId: Int? = null): QuoteDto

    @GET("/api/music-refs/quotes/{id}")
    suspend fun quote(@Path("id") id: Int): QuoteDto

    @POST("/api/music-refs/parties")
    suspend fun createParty(@Body body: PartyCreateRequest): PartySnapshotDto

    @POST("/api/music-refs/parties/join")
    suspend fun joinParty(@Body body: PartyJoinRequest): PartySnapshotDto

    @GET("/api/music-refs/parties/{code}")
    suspend fun party(@Path("code") code: String): PartySnapshotDto

    @POST("/api/music-refs/parties/{code}/start")
    suspend fun startParty(@Path("code") code: String, @Body body: PartyStartRequest): PartySnapshotDto

    @GET("/api/music-refs/parties/{code}/quotes")
    suspend fun partyQuotes(@Path("code") code: String): List<QuoteDto>

    @POST("/api/music-refs/parties/{code}/score")
    suspend fun updateScore(@Path("code") code: String, @Body body: PartyScoreRequest): PartySnapshotDto
}
