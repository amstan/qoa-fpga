// QOA predicts each audio sample based on the previously decoded ones
// using a “Sign-Sign Least Mean Squares Filter“ (LMS). This
// prediction plus the dequantized residual forms the final output
// sample.

module lms(
	// load interface for decoder, lms_state goes in here
	input wire load,
	input wire signed [15:0] load_history[0:3],
	input wire signed [15:0] load_weights[0:3],

	// async prediction, always available
	output reg signed [31:0] prediction,

	// update interface, to be used to advance the sample
	input wire update,
	input wire signed [31:0] sample,
	input wire signed [27:0] delta,

	input wire clk,
	input wire rst, // set to an initial state for encoding

	// allow a view into the internal state for the encoder to save them
	output reg signed [15:0] save_history[0:3],
	output reg signed [15:0] save_weights[0:3]
);

reg signed [15:0] history[0:3]; // TODO: Convert this to 32 bits
reg signed [15:0] weights[0:3]; // after I figure out how to cast nicely

always @ * begin
	save_history = history;
	save_weights = weights;

	// in spec [4]
	prediction = 0;
	for (integer i = 0; i < 4; i++) begin
		prediction += history[i] * weights[i];
	end
	prediction >>= 13; // TODO: parent needs ugly sign extension, maybe fix it here
	// TODO: consider sizing prediction port to be smaller since
	// we're throwing away bits anyway
end

always @ (posedge clk) begin

	if (update) begin
		// use delta to update weights, in spec [6]
		for (integer i = 0; i < 4; i++) begin
			weights[i] += history[i] < 0 ? -delta : delta;
		end

		// append sample to history, in spec [7]
		history[0:2] <= history[1:3];
		history[3] <= sample;
	end

	// TODO: Figure out what happens when load, update &
	// predict need to happen at the same time

	if (load) begin
		history <= load_history;
		weights <= load_weights;
	end

	if (rst) begin
		// TODO weights for the encoder initial state
		history <= '{default: 0};
	end
end

endmodule
